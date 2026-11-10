# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import Any, Dict, Optional, Tuple

import numpy as np
import torch

from core.enums import Maturity
from core.system_reporter import SystemReporter
from domain.value_objects import FleetDecisions
from engine.decision_telemetry_reporter import DecisionTelemetryReporter
from engine.evp_preemption_evaluator import EvpPreemptionEvaluator
from engine.fleet_batch_inferencer import FleetBatchInferencer
from engine.guardian_context_builder import GuardianContextBuilder
from models.actor_critic_tcn import ActorCriticNet
from models.pae import PredictiveAutoencoder
from utils.safety_rules import SafetyRules


class AgentEvaluator:
    """
    Encapsulates the intelligence and control loop of a single local agent over time.
    Measures operational timing using the injected StepTimer.
    Delegates EVP checks to EvpPreemptionEvaluator and safety context to GuardianContextBuilder (SRP).
    """

    def __init__(
        self,
        state_extractor: Any,
        input_preprocessor: Any,
        reward_computer: Any,
        action_authorizer: Any,
        action_supervisor: Any,
        maturity_manager: Any,
        locale_manager: Any,
        db_manager: Any = None,
    ) -> None:
        self.state_extractor = state_extractor
        self.input_preprocessor = input_preprocessor
        self.reward_computer = reward_computer
        self.action_authorizer = action_authorizer
        self.action_supervisor = action_supervisor
        self.maturity_manager = maturity_manager
        self.lm = locale_manager
        self.db_manager = db_manager
        self.batch_inferencer = FleetBatchInferencer()
        self._precomputed_fleet_decisions: Dict[
            str, Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]
        ] = {}
        self._precomputed_action_masks: Dict[str, torch.Tensor] = {}

    def _get_evp_preemption_state(self, tl_id: str) -> Optional[str]:
        return EvpPreemptionEvaluator.get_evp_preemption_state(tl_id)

    def _compute_physical_action_mask(
        self, tl_id: str, agent: Any, current_stage_idx: int, sim_time: float
    ) -> Optional[torch.Tensor]:
        """
        Builds a binary physical action mask [1, 2] -> [allow_advance (0), allow_keep (1)]
        enforcing yellow/all-red clearance, minimum green, and maximum green constraints.
        """
        if not isinstance(getattr(agent, "policy_net", None), ActorCriticNet):
            return None

        stage_codes_all = getattr(self.state_extractor, "tl_stage_codes", None)
        last_change_map = getattr(self.action_supervisor, "_last_stage_change_time", None)
        if not isinstance(stage_codes_all, dict) or not isinstance(last_change_map, dict):
            return None

        stage_codes = stage_codes_all.get(tl_id)
        if not isinstance(stage_codes, dict) or not stage_codes:
            return None

        state_str = str(stage_codes.get(current_stage_idx, "G")).upper()
        elapsed = float(sim_time) - float(last_change_map.get(tl_id, 0.0))

        allow_advance = True
        allow_keep = True

        if "Y" in state_str and "G" not in state_str:
            allow_advance = False
        elif "G" not in state_str and "Y" not in state_str:
            allow_advance = False
        else:
            min_green = SafetyRules.get_green()
            max_green = SafetyRules.get_max_green()
            if elapsed < min_green:
                allow_advance = False
            elif max_green > min_green and elapsed >= max_green:
                allow_keep = False

        if not allow_advance and not allow_keep:
            allow_keep = True

        device = getattr(agent, "device", torch.device("cpu"))
        return torch.tensor([[allow_advance, allow_keep]], dtype=torch.bool, device=device)

    def evaluate_agent(
        self,
        tl_id: str,
        agent: Any,
        current_stage_idx: int,
        traffic_data: dict,
        edges_data: dict,
        sim_time: float,
        guardian: Optional[Any],
        step_timer: Any,
        precomputed_state_data: Optional[Tuple[np.ndarray, torch.Tensor, np.ndarray]] = None,
        precomputed_pae_latent: Optional[torch.Tensor] = None,
    ) -> Tuple[Optional[int], str, bool, float, float, Dict[str, str]]:
        tls_lanes_state = self.state_extractor.get_phase_lane_states(tl_id, current_stage_idx)
        agent_maturity = self.maturity_manager.agent_maturity.get(tl_id, Maturity.CHILD)
        maturity_name = agent_maturity.name

        # 1. Extract State
        step_timer.start_phase()
        if "tls_telemetry" in traffic_data:
            telemetry = traffic_data["tls_telemetry"].get(tl_id, {})
            if telemetry.get("active_ped_calls", 0) > 0:
                logging.info(
                    f"🚶‍♂️ [AgentEvaluator] TL {tl_id}: Botão de pedestre pressionado detectado pelo hardware (UTMC/NTCIP)."
                )

        if precomputed_state_data is not None:
            state_vector, state_tensor, state_seq = precomputed_state_data
        else:
            state_vector = self.state_extractor.extract_state(traffic_data, tl_id, current_stage_idx)
            if len(state_vector) == 0:
                step_timer.stop_phase("extraction")
                return None, maturity_name, False, 0.0, 0.0, tls_lanes_state
            state_tensor, state_seq = self.input_preprocessor.prepare_tensor(tl_id, state_vector)
        step_timer.stop_phase("extraction")

        # 2. Agent Inference (Vectorized Fleet Hit or Single-Agent Forward)
        step_timer.start_phase()
        precomputed_decision = self._precomputed_fleet_decisions.get(tl_id)
        if precomputed_decision is not None:
            action_idx, action_log_prob, state_val, dist_entropy = precomputed_decision
        else:
            action_mask = self._precomputed_action_masks.get(tl_id)
            if action_mask is None:
                action_mask = self._compute_physical_action_mask(tl_id, agent, current_stage_idx, sim_time)
            if action_mask is not None:
                action_idx, action_log_prob, state_val, dist_entropy = agent.choose_action(
                    state_tensor,
                    precomputed_pae_latent=precomputed_pae_latent,
                    action_mask=action_mask,
                )
            else:
                action_idx, action_log_prob, state_val, dist_entropy = agent.choose_action(
                    state_tensor, precomputed_pae_latent=precomputed_pae_latent
                )
        step_timer.stop_phase("inference")

        action_int = action_idx.item()
        entropy_val = dist_entropy.item() if hasattr(dist_entropy, "item") else 0.0

        # 3. Compute Reward
        step_timer.start_phase()
        reward = self.reward_computer.calculate(tl_id, edges_data)
        step_timer.stop_phase("reward")

        # 5. Core Authorization
        step_timer.start_phase()
        raw_ts = traffic_data.get("timestamp", 0.0) if isinstance(traffic_data, dict) else 0.0
        is_auth, reason = self.action_authorizer.is_action_authorized(
            tl_id, agent_maturity, sim_time, raw_timestamp=raw_ts
        )
        step_timer.stop_phase("auth")

        # 0. Active Emergency Preemption Check (EVP)
        evp_override = self._get_evp_preemption_state(tl_id)
        override_state = evp_override if evp_override else "NORMAL"

        # 6. Guardian Veto Control / Emergency Override
        guardian_vetoed = False
        original_action_int = action_int
        step_timer.start_phase()
        if evp_override and is_auth and action_int == 0:
            v_label = evp_override.split(":", 1)[1] if ":" in evp_override else "Viatura"
            is_auth = False
            reason = f"PREEMPÇÃO EVP ATIVA ({v_label} no Corredor Verde)"
            guardian_vetoed = True
            logging.info(f"[AgentEvaluator] TL {tl_id} stage change VETOED by EVP Preemption: {v_label}")

            action_int = 1
            action_idx = torch.tensor([1], device=agent.device)
            with torch.no_grad():
                action_log_prob, _, _ = agent.evaluate(
                    state_tensor, action_idx, precomputed_pae_latent=precomputed_pae_latent
                )
        elif is_auth and action_int == 0 and guardian:
            context = GuardianContextBuilder.build_context(
                tl_id=tl_id,
                current_stage_idx=current_stage_idx,
                sim_time=sim_time,
                state_extractor=self.state_extractor,
                action_supervisor=self.action_supervisor,
            )
            guard_action, guard_reason = guardian.select_action(
                state_vector, context, precomputed_pae_latent=precomputed_pae_latent
            )

            if guard_action == guardian.ACTION_KEEP_STAGE:
                is_auth = False
                reason = f"VETADA PELO GUARDIÃO ({guard_reason})"
                guardian_vetoed = True
                logging.info(f"[AgentEvaluator] TL {tl_id} stage change VETOED by Guardian: {guard_reason}")

                action_int = 1
                action_idx = torch.tensor([1], device=agent.device)
                with torch.no_grad():
                    action_log_prob, _, _ = agent.evaluate(
                        state_tensor, action_idx, precomputed_pae_latent=precomputed_pae_latent
                    )
            else:
                logging.info(f"[AgentEvaluator] TL {tl_id} stage change ALLOWED by Guardian: {guard_reason}")
        step_timer.stop_phase("guardian")

        # 4. Store Experience
        agent.push_memory(state_seq, action_idx, action_log_prob, reward, False, state_val)

        # 7. Reporting & Telemetry
        action_str = (
            self.lm.get_string("actions.change_stage")
            if original_action_int == 0
            else self.lm.get_string("actions.keep_stage")
        )
        SystemReporter.report_agent_decision(self.lm, tl_id, maturity_name, action_str, is_auth, reason, override_state)

        DecisionTelemetryReporter.push_telemetry(
            self.db_manager, tl_id, evp_override, guardian_vetoed, reason
        )

        action_to_apply = action_int if (is_auth or guardian_vetoed) else None
        return action_to_apply, maturity_name, guardian_vetoed, reward, entropy_val, tls_lanes_state

    def evaluate_fleet(
        self,
        agents: Dict[str, Any],
        current_stages: Dict[str, Any],
        traffic_data: Dict[str, Any],
        edges_data: Dict[str, Any],
        sim_time: float,
        guardians: Dict[str, Any],
        step_timer: Any,
    ) -> FleetDecisions:
        actions_to_apply = {}
        tls_lanes_state = {}
        maturity_info = {}
        guardian_vetoed_any = False
        step_reward_sum = 0.0
        metrics_delta = {}

        # --- Vectorized Fleet Pre-Extraction & Batched PAE Encoding ---
        precomputed_states: Dict[str, Tuple[np.ndarray, torch.Tensor, np.ndarray]] = {}
        precomputed_latents: Dict[str, torch.Tensor] = {}

        # 1. Pre-extract and prepare tensors for all active agents
        for tl_id in agents.keys():
            current_stage_idx = current_stages.get(tl_id, 0)
            state_vector = self.state_extractor.extract_state(traffic_data, tl_id, current_stage_idx)
            if len(state_vector) > 0:
                state_tensor, state_seq = self.input_preprocessor.prepare_tensor(tl_id, state_vector)
                precomputed_states[tl_id] = (state_vector, state_tensor, state_seq)

        # 2. Locate universal PAE instance (if any)
        shared_pae = None
        for agent in agents.values():
            if getattr(agent, "shared_pae", None) is not None:
                shared_pae = agent.shared_pae
                break

        # 3. Parallel Batched PAE Forward Pass (with Heterogeneous Channel Padding & Valid-Dim Masking)
        if shared_pae is not None and precomputed_states:
            try:
                valid_tls = [tl for tl in agents.keys() if tl in precomputed_states]
                if valid_tls:
                    is_real_pae = isinstance(shared_pae, PredictiveAutoencoder)
                    tensors_to_batch = []
                    orig_dims = []
                    for tl in valid_tls:
                        t = precomputed_states[tl][1]
                        if is_real_pae and hasattr(t, "shape") and len(t.shape) >= 1:
                            orig_dims.append(int(t.shape[-1]))
                        if hasattr(shared_pae, "standardize_sequence"):
                            t = shared_pae.standardize_sequence(t)
                        if is_real_pae and hasattr(shared_pae, "pad_to_input_dim"):
                            t = shared_pae.pad_to_input_dim(t)
                        tensors_to_batch.append(t)

                    batch_tensor = torch.cat(tensors_to_batch, dim=0)
                    device_type = (
                        shared_pae.device.type
                        if hasattr(shared_pae, "device") and hasattr(shared_pae.device, "type")
                        else "cpu"
                    )
                    with torch.no_grad(), torch.amp.autocast(
                        device_type=device_type, enabled=(device_type == "cuda")
                    ):
                        if is_real_pae and orig_dims:
                            valid_dims_t = torch.tensor(
                                orig_dims, dtype=torch.long, device=batch_tensor.device
                            )
                            all_latents = shared_pae.encode(batch_tensor, valid_dims=valid_dims_t)
                        else:
                            all_latents = shared_pae.encode(batch_tensor)

                    for idx, tl in enumerate(valid_tls):
                        precomputed_latents[tl] = all_latents[idx : idx + 1]
            except Exception as e:
                logging.debug(f"[AgentEvaluator] Batched PAE encoding fallback: {e}")

        # 4. Compute Physical Action Masks & Vectorized Fleet Policy Inference (vmap)
        self._precomputed_action_masks = {}
        self._precomputed_fleet_decisions = {}
        try:
            for tl_id, agent in agents.items():
                if tl_id in precomputed_states:
                    mask = self._compute_physical_action_mask(
                        tl_id, agent, current_stages.get(tl_id, 0), sim_time
                    )
                    if mask is not None:
                        self._precomputed_action_masks[tl_id] = mask

            if precomputed_states:
                self._precomputed_fleet_decisions = self.batch_inferencer.infer_fleet(
                    agents=agents,
                    precomputed_states=precomputed_states,
                    precomputed_latents=precomputed_latents,
                    action_masks=self._precomputed_action_masks,
                )

            for tl_id, agent in agents.items():
                current_stage_idx = current_stages.get(tl_id, 0)
                guardian = guardians.get(tl_id)

                action, maturity_name, vetoed, reward, entropy, lanes_state = self.evaluate_agent(
                    tl_id,
                    agent,
                    current_stage_idx,
                    traffic_data,
                    edges_data,
                    sim_time,
                    guardian,
                    step_timer,
                    precomputed_state_data=precomputed_states.get(tl_id),
                    precomputed_pae_latent=precomputed_latents.get(tl_id),
                )

                tls_lanes_state[tl_id] = lanes_state
                maturity_info[tl_id] = maturity_name
                step_reward_sum += reward
                metrics_delta[tl_id] = (reward, entropy)

                if vetoed:
                    guardian_vetoed_any = True

                if action is not None:
                    actions_to_apply[tl_id] = action
        finally:
            self._precomputed_fleet_decisions.clear()
            self._precomputed_action_masks.clear()

        return FleetDecisions(
            actions=actions_to_apply,
            lanes_state=tls_lanes_state,
            maturity_info=maturity_info,
            step_reward_sum=step_reward_sum,
            guardian_vetoed_any=guardian_vetoed_any,
            metrics_delta=metrics_delta,
        )
