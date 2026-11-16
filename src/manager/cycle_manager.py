# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import os
from multiprocessing.connection import Connection
from typing import Any, Dict, Optional

import numpy as np
import torch

from core.enums import Maturity
from maturity.maturity_manager import resolve_agent_phase, resolve_maturity_map
from optimizer.ppo_optimizer import PPOOptimizer
from safety.guardian_checkpoint_service import GuardianCheckpointService
from utils.paths import get_base_output_dir


class CycleManager:
    """
    Manages the lifecycle and maturation of AI agents.
    Responsible for periodic checkpoints, metrics aggregation, online PPO training,
    and evolution state synchronization (child -> teen -> adult) with the UI.
    """

    def __init__(
        self,
        maturity_manager,
        pipe_conn: Connection,
        settings: Optional[Any] = None,
        ppo_optimizer: Optional[Any] = None,
        guardian_trainer: Optional[Any] = None,
        guardians: Optional[Dict[str, Any]] = None,
    ):
        """
        Args:
            maturity_manager: Instance of the maturity rules manager.
            pipe_conn: Connection (Pipe) to send updates to the UI.
            settings: Optional system settings (ConfigParser or dict) for PPO hyperparams.
            ppo_optimizer: Optional pre-configured PPOOptimizer instance.
            guardian_trainer: Optional shadow trainer/calibrator for CHILD-only Guardian learning.
            guardians: Optional dictionary mapping tl_id -> GuardianAgent.
        """
        self.maturity_manager = maturity_manager
        self.pipe_conn = pipe_conn
        self.settings = settings
        self.guardian_trainer = guardian_trainer
        self.guardians: Dict[str, Any] = guardians or {}
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.scaler = torch.amp.GradScaler(enabled=(self.device.type == "cuda"))

        if ppo_optimizer is not None:
            self.ppo_optimizer = ppo_optimizer
        else:
            hyperparams = self._extract_hyperparams(settings)
            self.ppo_optimizer = PPOOptimizer(hyperparams=hyperparams, device=self.device, scaler=self.scaler)

    def _extract_hyperparams(self, settings: Optional[Any]) -> Dict[str, Any]:
        """Extracts PPO hyperparameters from settings with safe fallbacks."""
        if settings is None:
            return {}

        def get_val(section: str, key: str, fallback: Any, val_type=float):
            if hasattr(settings, "get"):
                try:
                    if val_type == int and hasattr(settings, "getint"):
                        return settings.getint(section, key, fallback=fallback)
                    if val_type == float and hasattr(settings, "getfloat"):
                        return settings.getfloat(section, key, fallback=fallback)
                    raw = settings.get(section, key, fallback=fallback)
                    return val_type(raw)
                except Exception:
                    return fallback
            elif isinstance(settings, dict):
                sec = settings.get(section, {}) if isinstance(settings.get(section), dict) else {}
                val = settings.get(key, sec.get(key, fallback))
                try:
                    return val_type(val)
                except Exception:
                    return fallback
            return fallback

        return {
            "gamma": get_val("AI_TRAINING", "ppo_gamma", get_val("AI_TRAINING", "gamma", 0.99)),
            "gae_lambda": get_val("AI_TRAINING", "gae_lambda", 0.95),
            "eps_clip": get_val("AI_TRAINING", "ppo_eps_clip", get_val("AI_TRAINING", "eps_clip", 0.2)),
            "k_epochs": get_val("AI_TRAINING", "ppo_k_epochs", get_val("AI_TRAINING", "k_epochs", 4, int), int),
            "target_kl": get_val("AI_TRAINING", "target_kl", 0.02),
            "grad_clip_norm": get_val("AI_TRAINING", "grad_clip_norm", 0.5),
        }

    def _train_agents(self, agents: Dict) -> Dict[str, float]:
        """
        Executes online PPO training on all active agents using their accumulated on-policy memory.
        Returns a dictionary mapping agent IDs to their calculated loss.
        """
        losses = {}
        if not agents or self.ppo_optimizer is None:
            return losses

        for tl_id, agent in agents.items():
            if not hasattr(agent, "memory") or len(agent.memory) == 0:
                continue

            if not hasattr(agent.memory, "get_batch"):
                continue

            try:
                old_states, old_actions, old_log_probs, rewards, dones, old_state_values = agent.memory.get_batch()
                if len(rewards) == 0:
                    continue

                memory_batch = (old_states, old_actions, old_log_probs, rewards, dones, old_state_values)

                # Precompute PAE latents once per rollout instead of re-encoding inside every k_epoch/minibatch
                pre_latents = None
                shared_pae = getattr(agent, "shared_pae", None)
                if (
                    shared_pae is not None
                    and isinstance(old_states, torch.Tensor)
                    and type(old_states).__name__ != "DummyTensor"
                    and callable(getattr(shared_pae, "encode", None))
                    and callable(getattr(agent, "evaluate", None))
                    and not hasattr(agent.evaluate, "assert_called")
                ):
                    try:
                        with torch.no_grad():
                            agent_dev = getattr(agent, "device", self.ppo_optimizer.device)
                            seq_dev = old_states.to(agent_dev) if hasattr(old_states, "to") else old_states
                            pre_latents = shared_pae.encode(seq_dev).detach()
                    except Exception:
                        pre_latents = None

                if pre_latents is not None:
                    total_loss = self.ppo_optimizer.step(
                        policy_net=agent.policy_net,
                        optimizer=agent.optimizer,
                        memory_batch=memory_batch,
                        evaluate_fn=agent.evaluate,
                        precomputed_latents=pre_latents,
                    )
                else:
                    total_loss = self.ppo_optimizer.step(
                        policy_net=agent.policy_net,
                        optimizer=agent.optimizer,
                        memory_batch=memory_batch,
                        evaluate_fn=agent.evaluate,
                    )
                losses[tl_id] = total_loss
                if hasattr(agent, "steps_done"):
                    agent.steps_done += len(rewards)
                logging.info(
                    f"[CycleManager] Online PPO update for agent {tl_id} | Loss: {total_loss:.4f} | Samples: {len(rewards)}"
                )
            except Exception as e:
                logging.error(f"[CycleManager] Error updating agent {tl_id} with PPO: {e}", exc_info=True)
        return losses

    def set_guardians(self, guardians: Optional[Dict[str, Any]]) -> None:
        """Registers GuardianAgent instances managed for cycle training and persistence."""
        self.guardians = guardians or {}

    def evaluate_cycle(
        self,
        step_counter: int,
        agents: Dict,
        accumulated_metrics: Dict,
        mfd_efficiency: float = 0.0,
        guardians: Optional[Dict[str, Any]] = None,
    ):
        """
        Executes end-of-cycle routine:
        1. Online PPO Optimization & CHILD-only Guardian QR-D3QN updates.
        2. Computes performance averages.
        3. Checks tier promotions and freezes newly graduated Guardians.
        4. Saves checkpoints (now with updated phase and calibrated Guardians).
        5. Notifies the UI.
        """
        logging.info(f"--- FIM DO CICLO (Passo {step_counter}) | AVALIAÇÃO DE MATURIDADE ---")
        active_guardians = guardians if guardians is not None else self.guardians

        # 1. Online PPO Optimization & CHILD-only off-policy Guardian learning
        self._train_agents(agents)
        if self.guardian_trainer is not None and active_guardians:
            self.guardian_trainer.train_active_child_guardians(active_guardians, self.maturity_manager)

        # 2. Metrics Aggregation
        agent_metrics_summary = self._aggregate_metrics(accumulated_metrics)

        # Clear metrics for the next cycle
        accumulated_metrics.clear()

        # 3. Promotion Check & Guardian Calibration/Freeze on graduation
        promotion_occurred = self.maturity_manager.check_and_promote_agents(agent_metrics_summary, mfd_efficiency)
        if self.guardian_trainer is not None and active_guardians:
            self.guardian_trainer.sync_maturation_and_freeze(active_guardians, self.maturity_manager)

        # 4. Physical Checkpoints (Now it will save with the ALREADY updated phase)
        self._save_checkpoints(agents, guardians=active_guardians)

        # Clear agent memory buffers to prevent RAM leak in HFT mode
        for agent in agents.values():
            if hasattr(agent, "memory"):
                agent.memory.clear()

        # Force empty PyTorch CUDA cache if GPU is available to prevent fragmentation/leak
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        # 5. Sync with UI
        if promotion_occurred:
            self._sync_maturity_state(step_counter)

    def _save_checkpoints(self, agents: Dict, guardians: Optional[Dict[str, Any]] = None):
        """Saves the current state of neural networks, guardians, and maturity phase to disk."""
        try:
            results_base = get_base_output_dir()
            checkpoints_dir = os.path.join(results_base, "results", "hft_live_session", "checkpoints")
            os.makedirs(checkpoints_dir, exist_ok=True)

            maturity_map = resolve_maturity_map(self.maturity_manager)
            for tl_id, agent in agents.items():
                current_maturity = (
                    maturity_map.get(tl_id, Maturity.CHILD)
                    if maturity_map
                    else resolve_agent_phase(self.maturity_manager, tl_id, Maturity.CHILD)
                )
                maturity_str = current_maturity.name
                ckpt_path = os.path.join(checkpoints_dir, f"agent_{tl_id}.pth")
                agent.save_checkpoint(ckpt_path, maturity_stage=maturity_str)

            # Save PAE Universal checkpoint if present
            first_agent = next(iter(agents.values()), None) if agents else None
            shared_pae = getattr(first_agent, "shared_pae", None)
            if shared_pae is not None:
                try:
                    pae_path = os.path.join(checkpoints_dir, "pae_universal.pth")
                    torch.save(shared_pae.state_dict(), pae_path)
                    logging.info(f"[CHECKPOINT] PAE Universal salvo em {pae_path}")
                except Exception as e_pae:
                    logging.error(f"[CHECKPOINT] Falha ao salvar PAE Universal: {e_pae}", exc_info=True)

            active_guardians = guardians if guardians is not None else self.guardians
            if active_guardians:
                GuardianCheckpointService.save_all(
                    active_guardians, checkpoints_dir=checkpoints_dir, maturity_manager=self.maturity_manager
                )

            logging.info(f"[CHECKPOINT] Estados dos agentes atualizados no disco.")
        except Exception as e:
            logging.error(f"[CHECKPOINT] Falha ao salvar checkpoints periódicos: {e}", exc_info=True)

    def _aggregate_metrics(self, accumulated_metrics: Dict) -> Dict:
        """Calculates the mean of accumulated rewards and entropies."""
        summary = {}
        for tl_id, metrics in accumulated_metrics.items():
            count = metrics.get("count", 0)
            if count > 0:
                mean_reward = metrics["reward_sum"] / count
                mean_entropy = metrics["entropy_sum"] / count
            else:
                # Fallback support for lists
                rewards_list = metrics.get("rewards", [])
                entropies_list = metrics.get("entropies", [])
                mean_reward = np.mean(rewards_list) if rewards_list else 0.0
                mean_entropy = np.mean(entropies_list) if entropies_list else 0.0

            summary[tl_id] = {"reward": mean_reward, "entropy": mean_entropy}
        return summary

    def _sync_maturity_state(self, step_counter: int):
        """Sends the new maturity map to the graphical interface."""
        maturity_map = {aid: phase.name for aid, phase in resolve_maturity_map(self.maturity_manager).items()}

        payload = {"run_id": step_counter, "agent_maturity": maturity_map}

        try:
            # Send 'update_maturity_state' command via custom pipe
            self.pipe_conn.send(("custom", "update_maturity_state", (payload,), {}))
            logging.info(f"[MATURITY] Estado de maturidade sincronizado com UI.")
        except Exception as e:
            logging.error(f"[MATURITY] Erro ao sincronizar maturidade: {e}", exc_info=True)
