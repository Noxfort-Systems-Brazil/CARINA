# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Safe Off-Policy Shadow Trainer for GuardianAgent (`Maturity.CHILD` Only).

While `ActionAuthorizer` keeps physical signals on the deterministic local timing
plan during `Maturity.CHILD`, this trainer observes real signal phase changes and
traffic saturation outcomes to populate Prioritized Experience Replay (PER), updates
QR-D3QN safely via `DQNOptimizer` at cycle boundaries, and triggers quantile
calibration + permanent weight freezing upon graduation to `TEEN`/`ADULT`.
"""

import logging
from collections import deque
from typing import Any, Deque, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn

from src.engine.reward_calculator import RewardCalculator
from src.optimizer.dqn_optimizer import DQNOptimizer


def _cfg_val(settings: Any, section: str, key: str, fallback: Any, cast: Any) -> Any:
    """Safely extracts typed numeric configuration values across ConfigParser, dicts, or mocks."""
    try:
        getter = getattr(settings, "getint" if cast is int else "getfloat", None)
        if callable(getter):
            val = getter(section, key, fallback=fallback)
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                return cast(val)
    except Exception:
        pass
    if isinstance(settings, dict):
        raw = settings.get(section, {}).get(key, fallback) if isinstance(settings.get(section), dict) else fallback
        try:
            return cast(raw)
        except (TypeError, ValueError):
            pass
    return cast(fallback)


class GuardianShadowTrainer:
    """Executes safe off-policy shadow training for GuardianAgents during `Maturity.CHILD`."""

    SPILLBACK_THRESHOLD = RewardCalculator.SPILLBACK_OCCUPANCY_THRESHOLD

    def __init__(
        self,
        settings: Any = None,
        device: Optional[torch.device] = None,
        dqn_optimizer: Optional[Any] = None,
        updates_per_cycle: int = 16,
        min_replay_warmup: int = 32,
    ) -> None:
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.updates_per_cycle = max(1, int(updates_per_cycle))
        self.min_replay_warmup = max(8, int(min_replay_warmup))

        self.correct_action = _cfg_val(settings, "GUARDIAN_REWARDS", "correct_action", 50.0, float)
        self.punish_inaction = _cfg_val(settings, "GUARDIAN_REWARDS", "punish_inaction", -100.0, float)
        self.correct_inaction = _cfg_val(settings, "GUARDIAN_REWARDS", "correct_inaction", 5.0, float)
        self.punish_false_alarm = _cfg_val(settings, "GUARDIAN_REWARDS", "punish_false_alarm", -10.0, float)

        hyperparams = {
            "gamma": _cfg_val(settings, "GUARDIAN_AGENT", "gamma", 0.90, float),
            "batch_size": _cfg_val(settings, "GUARDIAN_AGENT", "batch_size", 128, int),
            "tau": _cfg_val(settings, "GUARDIAN_AGENT", "tau", 0.005, float),
            "grad_clip_norm": _cfg_val(settings, "GUARDIAN_AGENT", "grad_clip_norm", 1.0, float),
        }
        self.dqn_optimizer = dqn_optimizer or DQNOptimizer(hyperparams=hyperparams, device=self.device)

        self._shadow_deques: Dict[str, Deque[np.ndarray]] = {}
        self._prev_seq: Dict[str, torch.Tensor] = {}
        self._prev_stage: Dict[str, int] = {}
        self._prev_sat: Dict[str, float] = {}

    def reset(self) -> None:
        self._shadow_deques.clear()
        self._prev_seq.clear()
        self._prev_stage.clear()
        self._prev_sat.clear()

    @staticmethod
    def _resolve_phase_name(maturity_manager: Any, tl_id: str) -> str:
        from src.maturity.maturity_manager import resolve_agent_phase

        phase = resolve_agent_phase(maturity_manager, tl_id, default="CHILD")  # type: ignore[arg-type]
        return "CHILD" if phase is None else str(getattr(phase, "name", phase)).upper()

    @staticmethod
    def _extract_latest_frame(tl_id: str, agent: Any, guardian: Any) -> Optional[np.ndarray]:
        mem = getattr(agent, "memory", None)
        states = getattr(mem, "states", None)
        if states is not None and len(states) > 0:
            raw = states[-1]
            arr = (
                raw.detach().cpu().float().numpy()
                if isinstance(raw, torch.Tensor)
                else np.asarray(raw, dtype=np.float32)
            )
            return (arr[-1] if arr.ndim >= 2 else arr).reshape(-1).astype(np.float32)
        deques = getattr(guardian, "state_deques", None)
        if isinstance(deques, dict) and tl_id in deques and len(deques[tl_id]) > 0:
            return np.asarray(deques[tl_id][-1], dtype=np.float32).reshape(-1)
        return None

    def _compute_shadow_reward(
        self, a_real: int, prev_sat: float, curr_sat: float, incident: bool
    ) -> Tuple[float, bool]:
        spillback = (curr_sat >= self.SPILLBACK_THRESHOLD) or incident
        if a_real == 1:  # Physical stage changed (ACTION_CHANGE_STAGE)
            if spillback and (curr_sat >= prev_sat or incident or curr_sat >= 0.85):
                return self.punish_inaction, True
            if not spillback and curr_sat < 0.75:
                return self.correct_inaction, False
            return 0.0, spillback

        # Physical stage kept (ACTION_KEEP_STAGE)
        if not incident and prev_sat >= 0.70 and curr_sat <= prev_sat + 0.02:
            return self.correct_action, spillback
        if prev_sat < 0.65 and curr_sat < 0.70 and (curr_sat - prev_sat) > 0.05:
            return self.punish_false_alarm, False
        return (-25.0, True) if incident else (1.0, spillback)

    def _build_sequence_tensor(self, tl_id: str, frame: np.ndarray, guardian: Any) -> Optional[torch.Tensor]:
        seq_len = int(getattr(guardian, "TEMPORAL_SEQ_LEN", 8))
        if frame.size != int(getattr(guardian, "n_observations", frame.size)):
            return None
        dq = self._shadow_deques.setdefault(tl_id, deque(maxlen=seq_len))
        dq.append(frame)
        seq = list(dq)
        while len(seq) < seq_len:
            seq.insert(0, seq[0])
        return torch.from_numpy(np.asarray(seq, dtype=np.float32)).to(getattr(guardian, "device", self.device))

    def _record_calibration_sample(self, guardian: Any, prev_seq: torch.Tensor, spillback: bool) -> None:
        if not isinstance(getattr(nn, "Linear", None), type):
            return
        calibrator = getattr(guardian, "calibrator", None)
        policy_net = getattr(guardian, "policy_net", None)
        if calibrator is None or policy_net is None or not callable(policy_net):
            return
        try:
            with torch.no_grad():
                seq_b = prev_seq.unsqueeze(0)
                pae_latent = guardian._get_pae_latent(seq_b)
                if getattr(policy_net, "is_distributional", False) and callable(
                    getattr(policy_net, "forward_quantiles", None)
                ):
                    _, margin, spread = calibrator.compute_cvar_effective_q(
                        policy_net.forward_quantiles(seq_b, pae_latent)
                    )
                else:
                    _, margin = calibrator.compute_neural_prob(policy_net(seq_b, pae_latent))
                    spread = 1.0
                calibrator.record_child_observation(margin, spread, spillback)
        except Exception:
            pass

    def observe_step(
        self,
        traffic_data: Dict[str, Any],
        agents: Dict[str, Any],
        guardians: Dict[str, Any],
        current_stages: Dict[str, Any],
        maturity_manager: Any,
        sim_time: float,
        pae_mse: Optional[float] = None,
    ) -> None:
        """Records real controller transitions into Guardian PER during `CHILD` phase only."""
        if not guardians or maturity_manager is None:
            return
        incident = (
            float(traffic_data.get("emergency_brakes", 0) or 0) > 0 or float(traffic_data.get("teleports", 0) or 0) > 0
        )

        for tl_id, guardian in guardians.items():
            calibrator = getattr(guardian, "calibrator", None)
            if calibrator is not None and pae_mse is not None:
                calibrator.latest_pae_mse = float(pae_mse)

            if self._resolve_phase_name(maturity_manager, tl_id) != "CHILD":
                if callable(getattr(guardian, "freeze_for_deployment", None)) and not getattr(
                    guardian, "is_frozen", False
                ):
                    guardian.freeze_for_deployment()
                continue
            if getattr(guardian, "is_frozen", False):
                continue
            if calibrator is not None and not calibrator.is_calibrated:
                calibrator.child_learning_active = True

            frame = self._extract_latest_frame(tl_id, (agents or {}).get(tl_id), guardian)
            if frame is None or frame.size == 0:
                continue
            curr_seq = self._build_sequence_tensor(tl_id, frame, guardian)
            if curr_seq is None:
                continue

            curr_sat = calibrator.extract_saturation(frame) if calibrator is not None else float(np.max(frame))
            curr_stage = current_stages.get(tl_id)
            prev_seq, prev_stage = self._prev_seq.get(tl_id), self._prev_stage.get(tl_id)

            if prev_seq is not None and prev_stage is not None and curr_stage is not None:
                a_real = (
                    guardian.ACTION_CHANGE_STAGE if int(curr_stage) != int(prev_stage) else guardian.ACTION_KEEP_STAGE
                )
                r_safety, spillback = self._compute_shadow_reward(a_real, self._prev_sat[tl_id], curr_sat, incident)
                guardian.memory.push(prev_seq, a_real, curr_seq, r_safety)
                # Boost PER priority 4x on rare CHANGE actions / spillback events under fixed-time plans
                mem = guardian.memory
                if a_real == guardian.ACTION_CHANGE_STAGE or spillback:
                    if callable(getattr(mem, "boost_last_priority", None)):
                        mem.boost_last_priority(4.0)
                    elif (
                        isinstance(getattr(mem, "priorities", None), torch.Tensor)
                        and isinstance(getattr(mem, "ptr", None), int)
                        and isinstance(getattr(mem, "capacity", None), int)
                    ):
                        idx = (mem.ptr - 1) % mem.capacity
                        mem.priorities[idx] = max(float(mem.priorities[idx]), 4.0)
                self._record_calibration_sample(guardian, prev_seq, spillback)

            self._prev_seq[tl_id] = curr_seq
            if curr_stage is not None:
                self._prev_stage[tl_id] = int(curr_stage)
            self._prev_sat[tl_id] = curr_sat

    def train_active_child_guardians(self, guardians: Dict[str, Any], maturity_manager: Any) -> Dict[str, float]:
        """Executes end-of-cycle off-policy QR-D3QN updates exclusively for `CHILD` guardians."""
        losses: Dict[str, float] = {}
        if not guardians or maturity_manager is None:
            return losses

        for tl_id, guardian in guardians.items():
            if self._resolve_phase_name(maturity_manager, tl_id) != "CHILD" or getattr(guardian, "is_frozen", False):
                continue
            if getattr(guardian, "target_net", None) is None or getattr(guardian, "optimizer", None) is None:
                continue
            mem = getattr(guardian, "memory", None)
            if mem is None or len(mem) < min(int(getattr(guardian, "batch_size", 128)), self.min_replay_warmup):
                continue

            eff_batch = min(int(getattr(guardian, "batch_size", 128)), len(mem))
            self.dqn_optimizer.batch_size = max(1, eff_batch)
            n_updates = min(self.updates_per_cycle, max(4, len(mem) // 16))

            loss_acc: List[float] = []
            for _ in range(n_updates):
                loss_val = self.dqn_optimizer.step(
                    policy_net=guardian.policy_net,
                    target_net=guardian.target_net,
                    optimizer=guardian.optimizer,
                    memory=mem,
                    forward_policy=guardian.forward_policy,
                    forward_target=guardian.forward_target,
                    forward_policy_quantiles=guardian.forward_policy_quantiles,
                    forward_target_quantiles=guardian.forward_target_quantiles,
                )
                self.dqn_optimizer.soft_update_target_net(guardian.policy_net, guardian.target_net)
                guardian.steps_done = int(getattr(guardian, "steps_done", 0)) + 1
                if getattr(guardian, "calibrator", None) is not None:
                    guardian.calibrator.record_td_loss(float(loss_val))
                loss_acc.append(float(loss_val))

            if hasattr(guardian, "eval"):
                guardian.eval()
            if loss_acc:
                losses[tl_id] = float(np.mean(loss_acc))
                logging.info(
                    f"[GuardianShadowTrainer] CHILD cycle update TL={tl_id} | "
                    f"Loss={losses[tl_id]:.4f} | Steps={guardian.steps_done} | Replay={len(mem)}"
                )
        return losses

    def sync_maturation_and_freeze(self, guardians: Dict[str, Any], maturity_manager: Any) -> List[str]:
        """Calibrates and permanently freezes any Guardian promoted beyond `CHILD`."""
        newly_frozen: List[str] = []
        if not guardians or maturity_manager is None:
            return newly_frozen

        for tl_id, guardian in guardians.items():
            phase = self._resolve_phase_name(maturity_manager, tl_id)
            if phase != "CHILD" and not getattr(guardian, "is_frozen", False):
                stats = (
                    guardian.finalize_child_calibration()
                    if callable(getattr(guardian, "finalize_child_calibration", None))
                    else {}
                )
                if callable(getattr(guardian, "freeze_for_deployment", None)):
                    guardian.freeze_for_deployment()
                else:
                    guardian.is_frozen = True
                newly_frozen.append(tl_id)
                logging.info(f"[GuardianShadowTrainer] Guardian TL={tl_id} graduated to {phase} & FROZEN | {stats}")
        if (
            newly_frozen
            and hasattr(torch, "cuda")
            and callable(getattr(torch.cuda, "is_available", None))
            and torch.cuda.is_available()
        ):
            try:
                torch.cuda.empty_cache()
            except Exception:
                pass
        return newly_frozen
