# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from collections import defaultdict
import logging
from typing import Any, Dict, Optional

import numpy as np
import torch
import torch.nn.functional as F

from core.episode_reporter import EpisodeReporter
from core.system_reporter import SystemReporter
from drivers.hardware_stage_actuator import HardwareStageActuator
from engine.agent_evaluator import AgentEvaluator
from engine.online_pae_trainer import OnlinePAETrainer
from engine.step_telemetry_publisher import StepTelemetryPublisher
from engine.step_timer import StepTimer
from manager.stage_transition_manager import StageTransitionManager
from mfd.mfd_processor import MFDProcessor


class StepProcessor:
    """
    Pure Facade & Orchestrator for the simulation step (HFT Step) pipeline.
    Adheres strictly to SOLID, Clean Architecture, and DDD.
    """

    def __init__(
        self,
        settings: Any,
        locale_manager: Any,
        step_timer: StepTimer,
        agent_evaluator: AgentEvaluator,
        stage_transition_manager: StageTransitionManager,
        action_supervisor: Any,
        online_pae_trainer: OnlinePAETrainer,
        mfd_processor: MFDProcessor,
        hardware_actuator: HardwareStageActuator,
        telemetry_publisher: StepTelemetryPublisher,
        cycle_manager: Any,
        episode_reporter: EpisodeReporter,
        mfd: Any = None,
        state_reconciler: Any = None,
        state_extractor: Any = None,
    ) -> None:
        self.settings = settings
        self.lm = locale_manager

        # Injected SRP Collaborators
        self.step_timer = step_timer
        self.agent_evaluator = agent_evaluator
        self.stage_transition_manager = stage_transition_manager
        self.action_supervisor = action_supervisor
        self.online_pae_trainer = online_pae_trainer
        self.mfd_processor = mfd_processor
        self.hardware_actuator = hardware_actuator
        self.telemetry_publisher = telemetry_publisher
        self.cycle_manager = cycle_manager
        self.episode_reporter = episode_reporter

        # Environment / Bridge references
        self.state_reconciler = state_reconciler
        self.state_extractor = state_extractor

        # Global ST-GATv2 Strategist Coordination
        self.strategist: Optional[Any] = None
        try:
            raw_strat_freq = self.settings.getfloat("GAT_STRATEGIST", "update_frequency_seconds", fallback=5.0)
            self.strategist_update_frequency = (
                float(raw_strat_freq) if isinstance(raw_strat_freq, (int, float)) else 5.0
            )
        except Exception:
            self.strategist_update_frequency = 5.0
        self._last_strategist_update_time: float = -1e9
        self._prev_strategist_node_seq: Optional[torch.Tensor] = None
        self._last_fleet_mean_reward: float = 0.0

        # Session State Variables
        self.step_counter = 0
        self.start_time_offset: Optional[float] = None
        self.current_stages: Dict[str, Any] = {}
        self.accumulated_metrics = defaultdict(lambda: {"reward_sum": 0.0, "entropy_sum": 0.0, "count": 0})
        self.log_step_progress = True
        self.guardians: Dict[str, Any] = {}
        self.episode_steps = self.settings.getint("AI_TRAINING", "episode_max_steps", fallback=100)

        # Episode Tracking
        self._episode_counter = 0
        self._episode_total_reward = 0.0
        self._episode_steps_in_current = 0

    def reset_state(self) -> None:
        """Resets counters and collaborators for a new session or map."""
        self.mfd_processor.reset()
        self.hardware_actuator.reset()
        self.action_supervisor.reset()
        self.online_pae_trainer.reset()

        if hasattr(self.agent_evaluator, "input_preprocessor") and hasattr(
            self.agent_evaluator.input_preprocessor, "reset"
        ):
            self.agent_evaluator.input_preprocessor.reset()

        self.step_counter = 0
        self.start_time_offset = None
        self.current_stages.clear()
        self.accumulated_metrics.clear()
        self._episode_counter = 0
        self._episode_total_reward = 0.0
        self._episode_steps_in_current = 0
        self._last_strategist_update_time = -1e9
        self._prev_strategist_node_seq = None
        self._last_fleet_mean_reward = 0.0

    def set_strategist(self, strategist: Optional[Any]) -> None:
        """Configures the global ST-GATv2 Strategist agent for HFT network coordination."""
        self.strategist = strategist
        self._last_strategist_update_time = -1e9
        self._prev_strategist_node_seq = None

    def set_current_phases(self, phases: Dict[str, Any]) -> None:
        """Sets the current traffic light phase states."""
        self.current_stages = phases

    def set_guardians(self, guardians: Dict[str, Any]) -> None:
        """Configures safety guardian instances for each junction."""
        self.guardians = guardians

    def set_episode_steps(self, steps: int) -> None:
        """Dynamically updates the episode step boundary based on network topology."""
        if steps > 0:
            self.episode_steps = int(steps)
            logging.info(f"[StepProcessor] Dynamic episode steps updated: {self.episode_steps}")

    def process_hft_step(self, traffic_data: Dict[str, Any], agents: Dict[str, Any]) -> None:
        """
        Orchestrates a single simulation step based on Real-Time Traffic Data.
        Executes a strictly linear pipeline across SRP collaborators.
        """
        self.step_timer.start_step()

        # 1. Advance simulation clock
        sim_time = self._update_clock(traffic_data)

        # 2. Safety Stage Transitions
        self.stage_transition_manager.auto_advance_transitions(sim_time, self.current_stages)
        if self.log_step_progress:
            SystemReporter.report_step_start(self.lm, self.step_counter, sim_time, "AUTOMATIC")

        # 2.5 Global ST-GATv2 Strategic Coordination (Periodic Macro-Graph Context)
        if self.strategist is not None and (sim_time - self._last_strategist_update_time) >= self.strategist_update_frequency:
            self._update_strategic_coordination(traffic_data, agents, sim_time)

        # 3. Fleet Agent Evaluation
        edges_data = traffic_data.get("edges", {})
        decisions = self.agent_evaluator.evaluate_fleet(
            agents=agents,
            current_stages=self.current_stages,
            traffic_data=traffic_data,
            edges_data=edges_data,
            sim_time=sim_time,
            guardians=self.guardians,
            step_timer=self.step_timer,
        )
        self._record_metrics(decisions)

        # 4. Action Execution & Software Phase Update
        if decisions.actions:
            self.action_supervisor.apply_actions(decisions.actions, sim_time, self.current_stages)
            self.stage_transition_manager.apply_software_transitions(
                decisions.actions, sim_time, self.current_stages
            )

        # 5. Online Continuous PAE Training (Self-Supervised Learning)
        self.online_pae_trainer.train_step(sim_time, agents)

        # 6. Step Timer Finalization
        self.step_timer.log_and_finish_step(decisions.guardian_vetoed_any, self.log_step_progress)

        # 7. Episode Boundary & Reporting Check
        self._handle_episode_boundary(agents)

        # 8. MFD Computation
        mfd_data = self.mfd_processor.process_step(
            edges_data=edges_data,
            sim_time=sim_time,
            agents_keys=list(agents.keys()),
            step_counter=self.step_counter,
            episode_steps=self.episode_steps,
        )

        # 9. Hardware Stage Synchronization
        self.hardware_actuator.sync_hardware_stages(
            action_supervisor=self.action_supervisor,
            current_stages=self.current_stages,
            state_extractor=self.state_extractor,
            state_reconciler=self.state_reconciler,
        )

        # 10. Outbound Telemetry Dispatch
        self.telemetry_publisher.publish(
            sim_time=sim_time,
            edges_data=edges_data,
            current_stages=self.current_stages,
            tls_lanes_state=decisions.lanes_state,
            maturity_info=decisions.maturity_info,
            mfd_data=mfd_data,
        )

    # --- Private Pipeline Helpers ---

    def _update_clock(self, traffic_data: Dict[str, Any]) -> float:
        """Calculates simulation time offset and updates step counters."""
        raw_timestamp = traffic_data.get("timestamp", 0)
        if self.start_time_offset is None:
            self.start_time_offset = raw_timestamp
        sim_time = raw_timestamp - self.start_time_offset
        self.step_counter += 1
        self._episode_steps_in_current += 1
        return sim_time

    def _record_metrics(self, decisions: Any) -> None:
        """Accumulates episode rewards and per-agent metrics."""
        self._episode_total_reward += decisions.step_reward_sum
        if decisions.metrics_delta:
            self._last_fleet_mean_reward = float(decisions.step_reward_sum) / max(1, len(decisions.metrics_delta))
        for tl_id, (reward, entropy) in decisions.metrics_delta.items():
            self.accumulated_metrics[tl_id]["reward_sum"] += reward
            self.accumulated_metrics[tl_id]["entropy_sum"] += entropy
            self.accumulated_metrics[tl_id]["count"] += 1

    def _update_strategic_coordination(
        self, traffic_data: Dict[str, Any], agents: Dict[str, Any], sim_time: float
    ) -> None:
        """
        Builds the network-wide temporal node tensor [N, T, F], executes online
        self-supervised future forecasting + CTDE global value updates on STGATv2Lite,
        and distributes fresh strategic context vectors to active LocalAgents.
        """
        if self.strategist is None:
            return

        try:
            num_nodes = getattr(self.strategist, "num_nodes", 0)
            tls_id_to_idx = getattr(self.strategist, "tls_id_to_idx", {})
            if not isinstance(num_nodes, int) or num_nodes <= 0 or not isinstance(tls_id_to_idx, dict):
                return

            raw_dim = getattr(getattr(self.strategist, "model", None), "input_dim", 16)
            target_dim = int(raw_dim) if isinstance(raw_dim, int) and raw_dim > 0 else 16

            ip = getattr(self.agent_evaluator, "input_preprocessor", None)
            raw_seq_len = getattr(ip, "sequence_length", 12)
            seq_len = int(raw_seq_len) if isinstance(raw_seq_len, int) and raw_seq_len > 0 else 12
            state_history = getattr(ip, "state_history", {}) if ip is not None else {}

            node_array = np.zeros((num_nodes, seq_len, target_dim), dtype=np.float32)

            for tl_id, node_idx in tls_id_to_idx.items():
                if not isinstance(node_idx, int) or node_idx < 0 or node_idx >= num_nodes:
                    continue

                frames = []
                if isinstance(state_history, dict) and tl_id in state_history and len(state_history[tl_id]) > 0:
                    frames = list(state_history[tl_id])[-seq_len:]

                if self.state_extractor is not None and hasattr(self.state_extractor, "extract_state"):
                    try:
                        curr_vec = self.state_extractor.extract_state(
                            traffic_data, tl_id, self.current_stages.get(tl_id, 0)
                        )
                        if isinstance(curr_vec, np.ndarray) and curr_vec.size > 0:
                            frames = (frames[-(seq_len - 1) :] if seq_len > 1 else []) + [curr_vec]
                    except Exception:
                        pass

                if frames:
                    start_t = max(0, seq_len - len(frames))
                    for offset, frame in enumerate(frames[-seq_len:]):
                        arr = np.asarray(frame, dtype=np.float32).reshape(-1)
                        copy_dim = min(arr.shape[0], target_dim)
                        if copy_dim > 0:
                            node_array[node_idx, start_t + offset, :copy_dim] = arr[:copy_dim]

            device = getattr(self.strategist, "device", torch.device("cpu"))
            node_seq = torch.as_tensor(node_array, dtype=torch.float32, device=device)

            # Online Self-Supervised Next-Step Forecasting + CTDE Global Value Training
            if (
                self._prev_strategist_node_seq is not None
                and hasattr(self._prev_strategist_node_seq, "shape")
                and self._prev_strategist_node_seq.shape == node_seq.shape
                and getattr(self.strategist, "edge_index", None) is not None
                and hasattr(self.strategist, "update")
            ):
                try:
                    target_next = node_seq[:, -1, :]
                    self.strategist.train(True)
                    model_out = self.strategist.model(
                        self._prev_strategist_node_seq,
                        self.strategist.edge_index,
                        edge_attr=getattr(self.strategist, "edge_attr", None),
                        return_prediction=True,
                        return_value=True,
                    )
                    if isinstance(model_out, tuple) and len(model_out) == 3:
                        _, pred_next, global_val = model_out
                        pred_loss = F.smooth_l1_loss(pred_next, target_next)
                        val_target = torch.full_like(global_val, float(self._last_fleet_mean_reward))
                        val_loss = F.smooth_l1_loss(global_val, val_target)
                        self.strategist.update(pred_loss + 0.5 * val_loss)
                    elif isinstance(model_out, tuple) and len(model_out) == 2:
                        _, pred_next = model_out
                        self.strategist.update(F.smooth_l1_loss(pred_next, target_next))
                except Exception as e_upd:
                    logging.debug(f"[StepProcessor] Strategist online update skipped: {e_upd}")
                finally:
                    if hasattr(self.strategist, "eval"):
                        self.strategist.eval()

            strategic_vectors = self.strategist.get_strategic_vectors(node_seq)
            self._prev_strategist_node_seq = node_seq.detach() if hasattr(node_seq, "detach") else node_seq
            self._last_strategist_update_time = sim_time

            for tl_id, agent in agents.items():
                idx = self.strategist.get_node_index(tl_id) if hasattr(self.strategist, "get_node_index") else -1
                if isinstance(idx, int) and 0 <= idx < getattr(strategic_vectors, "shape", [0])[0]:
                    if hasattr(agent, "set_strategic_context"):
                        vec = strategic_vectors[idx : idx + 1]
                        agent.set_strategic_context(vec.detach() if hasattr(vec, "detach") else vec)
        except Exception as e_strat:
            logging.debug(f"[StepProcessor] Strategic coordination skipped: {e_strat}")

    def _handle_episode_boundary(self, agents: Dict[str, Any]) -> None:
        """Handles episode completion evaluation and reporting."""
        if self.step_counter % self.episode_steps != 0:
            return

        self._episode_counter += 1
        mfd_efficiency = self.mfd_processor.get_latest_efficiency()
        self.cycle_manager.evaluate_cycle(self.step_counter, agents, self.accumulated_metrics, mfd_efficiency)
        self.episode_reporter.report_episode_bulletin(agents, self._episode_counter, self._episode_total_reward)

        self._episode_total_reward = 0.0
        self._episode_steps_in_current = 0
