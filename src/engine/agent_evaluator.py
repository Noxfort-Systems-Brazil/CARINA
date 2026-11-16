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
from engine.action_veto_resolver import ActionVetoResolver
from engine.batched_pae_encoder import BatchedPAEEncoder
from engine.decision_telemetry_reporter import DecisionTelemetryReporter
from engine.evp_preemption_evaluator import EvpPreemptionEvaluator
from engine.fleet_batch_inferencer import FleetBatchInferencer
from engine.physical_action_masker import PhysicalActionMasker

try:
    from interfaces.engine import IBatchedPAEEncoder, IPhysicalActionMasker
    from maturity.maturity_manager import resolve_agent_phase
except ImportError:
    from src.interfaces.engine import IBatchedPAEEncoder, IPhysicalActionMasker
    from src.maturity.maturity_manager import resolve_agent_phase


class AgentEvaluator:
    """
    Orchestrates tactical fleet evaluation across extraction, batched PAE encoding,
    physical masking, vectorized inference, authorization, EVP/Guardian vetoes, and telemetry.
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
        action_masker: Optional[IPhysicalActionMasker] = None,
        pae_encoder: Optional[IBatchedPAEEncoder] = None,
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
        self.action_masker: IPhysicalActionMasker = action_masker or PhysicalActionMasker(
            state_extractor=state_extractor, action_supervisor=action_supervisor
        )
        self.pae_encoder: IBatchedPAEEncoder = pae_encoder or BatchedPAEEncoder()
        self.veto_resolver = ActionVetoResolver(state_extractor=state_extractor, action_supervisor=action_supervisor)
        self._precomputed_fleet_decisions: Dict[str, Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]] = {}
        self._precomputed_fleet_cpu: Dict[str, Tuple[int, float, np.ndarray, np.ndarray, np.ndarray]] = {}
        self._precomputed_action_masks: Dict[str, torch.Tensor] = {}
        self.log_decisions: bool = True

    def _get_evp_preemption_state(self, tl_id: str) -> Optional[str]:
        return EvpPreemptionEvaluator.get_evp_preemption_state(tl_id)

    def _compute_physical_action_mask(
        self, tl_id: str, agent: Any, current_stage_idx: int, sim_time: float
    ) -> Optional[torch.Tensor]:
        return self.action_masker.compute_mask(tl_id, agent, current_stage_idx, sim_time)

    def _run_single_inference(
        self,
        tl_id: str,
        agent: Any,
        current_stage_idx: int,
        sim_time: float,
        state_tensor: torch.Tensor,
        precomputed_pae_latent: Optional[torch.Tensor],
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        precomputed_decision = self._precomputed_fleet_decisions.get(tl_id)
        if precomputed_decision is not None:
            return precomputed_decision

        action_mask = self._precomputed_action_masks.get(tl_id)
        if action_mask is None:
            action_mask = self._compute_physical_action_mask(tl_id, agent, current_stage_idx, sim_time)
        if action_mask is not None:
            return agent.choose_action(
                state_tensor,
                precomputed_pae_latent=precomputed_pae_latent,
                action_mask=action_mask,
            )
        return agent.choose_action(state_tensor, precomputed_pae_latent=precomputed_pae_latent)

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
        agent_maturity = resolve_agent_phase(self.maturity_manager, tl_id, Maturity.CHILD)
        maturity_name = agent_maturity.name

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

        step_timer.start_phase()
        action_idx, action_log_prob, state_val, dist_entropy = self._run_single_inference(
            tl_id, agent, current_stage_idx, sim_time, state_tensor, precomputed_pae_latent
        )
        step_timer.stop_phase("inference")

        cpu_dec = self._precomputed_fleet_cpu.get(tl_id) if tl_id in self._precomputed_fleet_decisions else None
        if cpu_dec is not None:
            action_int, entropy_val, push_act, push_lp, push_val = cpu_dec
        else:
            action_int = action_idx.item()
            entropy_val = dist_entropy.item() if hasattr(dist_entropy, "item") else 0.0
            push_act, push_lp, push_val = action_idx, action_log_prob, state_val

        step_timer.start_phase()
        reward = self.reward_computer.calculate(tl_id, edges_data)
        step_timer.stop_phase("reward")

        step_timer.start_phase()
        raw_ts = traffic_data.get("timestamp", 0.0) if isinstance(traffic_data, dict) else 0.0
        is_auth, reason = self.action_authorizer.is_action_authorized(
            tl_id, agent_maturity, sim_time, raw_timestamp=raw_ts
        )
        step_timer.stop_phase("auth")

        evp_override = self._get_evp_preemption_state(tl_id)
        override_state = evp_override if evp_override else "NORMAL"
        original_action_int = action_int

        step_timer.start_phase()
        action_int, action_idx, action_log_prob, is_auth, reason, guardian_vetoed = self.veto_resolver.resolve(
            tl_id,
            agent,
            guardian,
            current_stage_idx,
            sim_time,
            state_vector,
            state_tensor,
            precomputed_pae_latent,
            action_int,
            action_idx,
            action_log_prob,
            is_auth,
            reason,
            evp_override,
        )
        step_timer.stop_phase("guardian")

        if guardian_vetoed:
            agent.push_memory(state_seq, action_int, action_log_prob, reward, False, push_val)
        else:
            agent.push_memory(state_seq, push_act, push_lp, reward, False, push_val)

        if self.log_decisions or not is_auth or guardian_vetoed or bool(evp_override):
            action_str = (
                self.lm.get_string("actions.change_stage")
                if original_action_int == 0
                else self.lm.get_string("actions.keep_stage")
            )
            SystemReporter.report_agent_decision(
                self.lm, tl_id, maturity_name, action_str, is_auth, reason, override_state
            )
        DecisionTelemetryReporter.push_telemetry(self.db_manager, tl_id, evp_override, guardian_vetoed, reason)

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
        actions_to_apply: Dict[str, int] = {}
        tls_lanes_state: Dict[str, Dict[str, str]] = {}
        maturity_info: Dict[str, str] = {}
        guardian_vetoed_any = False
        step_reward_sum = 0.0
        metrics_delta: Dict[str, Tuple[float, float]] = {}

        precomputed_states: Dict[str, Tuple[np.ndarray, torch.Tensor, np.ndarray]] = {}
        for tl_id in agents.keys():
            current_stage_idx = current_stages.get(tl_id, 0)
            state_vector = self.state_extractor.extract_state(traffic_data, tl_id, current_stage_idx)
            if len(state_vector) > 0:
                state_tensor, state_seq = self.input_preprocessor.prepare_tensor(tl_id, state_vector)
                precomputed_states[tl_id] = (state_vector, state_tensor, state_seq)

        precomputed_latents = self.pae_encoder.encode_fleet(agents, precomputed_states)

        self._precomputed_action_masks = {}
        self._precomputed_fleet_decisions = {}
        self._precomputed_fleet_cpu = {}
        try:
            for tl_id, agent in agents.items():
                if tl_id in precomputed_states:
                    mask = self._compute_physical_action_mask(tl_id, agent, current_stages.get(tl_id, 0), sim_time)
                    if mask is not None:
                        self._precomputed_action_masks[tl_id] = mask

            if precomputed_states:
                self._precomputed_fleet_decisions = self.batch_inferencer.infer_fleet(
                    agents=agents,
                    precomputed_states=precomputed_states,
                    precomputed_latents=precomputed_latents,
                    action_masks=self._precomputed_action_masks,
                )
                cpu_map = getattr(self.batch_inferencer, "last_cpu_decisions", None)
                if isinstance(cpu_map, dict):
                    self._precomputed_fleet_cpu = cpu_map

            for tl_id, agent in agents.items():
                action, maturity_name, vetoed, reward, entropy, lanes_state = self.evaluate_agent(
                    tl_id,
                    agent,
                    current_stages.get(tl_id, 0),
                    traffic_data,
                    edges_data,
                    sim_time,
                    guardians.get(tl_id),
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
            self._precomputed_fleet_cpu.clear()
            self._precomputed_action_masks.clear()

        return FleetDecisions(
            actions=actions_to_apply,
            lanes_state=tls_lanes_state,
            maturity_info=maturity_info,
            step_reward_sum=step_reward_sum,
            guardian_vetoed_any=guardian_vetoed_any,
            metrics_delta=metrics_delta,
        )
