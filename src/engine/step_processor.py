# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from collections import defaultdict
from typing import Any, Dict, Optional

from core.episode_reporter import EpisodeReporter
from core.system_reporter import SystemReporter
from drivers.hardware_stage_actuator import HardwareStageActuator
from engine.agent_evaluator import AgentEvaluator
from engine.hardware_telemetry_synchronizer import HardwareTelemetrySynchronizer
from engine.online_pae_trainer import OnlinePAETrainer
from engine.step_telemetry_publisher import StepTelemetryPublisher
from engine.step_timer import StepTimer
from engine.strategic_coordinator import StrategicCoordinator
from manager.stage_transition_manager import StageTransitionManager
from mfd.mfd_processor import MFDProcessor


class StepProcessor:
    """
    Pure Facade & Orchestrator for the simulation step (HFT Step) pipeline.
    Adheres strictly to SOLID, Clean Architecture, and DDD by delegating telemetry ingestion,
    strategic tensor coordination, evaluation, actuation, and reporting to injected collaborators.
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
        state_reconciler: Any = None,
        state_extractor: Any = None,
        hardware_synchronizer: Optional[HardwareTelemetrySynchronizer] = None,
        strategic_coordinator: Optional[StrategicCoordinator] = None,
        guardian_shadow_trainer: Optional[Any] = None,
        maturity_manager: Optional[Any] = None,
    ) -> None:
        self.settings = settings
        self.lm = locale_manager
        self.guardian_shadow_trainer = guardian_shadow_trainer
        self.maturity_manager = maturity_manager

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
        self._state_reconciler = state_reconciler
        self._state_extractor = state_extractor

        self.hardware_synchronizer = hardware_synchronizer or HardwareTelemetrySynchronizer(
            action_supervisor=action_supervisor,
            state_extractor=state_extractor,
            state_reconciler=state_reconciler,
            telemetry_publisher=telemetry_publisher,
        )

        try:
            raw_strat_freq = self.settings.getfloat("GAT_STRATEGIST", "update_frequency_seconds", fallback=5.0)
            strat_freq = float(raw_strat_freq) if isinstance(raw_strat_freq, (int, float)) else 5.0
        except Exception:
            strat_freq = 5.0

        self.strategic_coordinator = strategic_coordinator or StrategicCoordinator(
            update_frequency_seconds=strat_freq,
            agent_evaluator=agent_evaluator,
            state_extractor=state_extractor,
        )

        # Session State Variables
        self.step_counter = 0
        self.start_time_offset: Optional[float] = None
        self.current_stages: Dict[str, Any] = {}
        self.accumulated_metrics = defaultdict(lambda: {"reward_sum": 0.0, "entropy_sum": 0.0, "count": 0})
        self.log_step_progress = self._resolve_log_step_progress(settings)
        self.guardians: Dict[str, Any] = {}
        self.episode_steps = self.settings.getint("AI_TRAINING", "episode_max_steps", fallback=100)

        # Episode & Fleet Reward Tracking
        self._episode_counter = 0
        self._episode_total_reward = 0.0
        self._episode_steps_in_current = 0
        self._last_fleet_mean_reward: float = 0.0

    @staticmethod
    def _resolve_log_step_progress(settings: Any) -> bool:
        try:
            getter = getattr(settings, "getboolean", None)
            val = getter("LOGGING", "log_step_progress", fallback=False) if callable(getter) else None
            if isinstance(val, bool):
                return val
            if isinstance(settings, dict) and isinstance(settings.get("LOGGING"), dict):
                return str(settings["LOGGING"].get("log_step_progress", False)).strip().lower() in (
                    "1",
                    "true",
                    "yes",
                    "on",
                )
        except Exception:
            pass
        return False

    @property
    def state_reconciler(self) -> Any:
        return self._state_reconciler

    @state_reconciler.setter
    def state_reconciler(self, value: Any) -> None:
        self._state_reconciler = value
        if getattr(self, "hardware_synchronizer", None) is not None:
            self.hardware_synchronizer.state_reconciler = value

    @property
    def state_extractor(self) -> Any:
        return self._state_extractor

    @state_extractor.setter
    def state_extractor(self, value: Any) -> None:
        self._state_extractor = value
        if getattr(self, "hardware_synchronizer", None) is not None:
            self.hardware_synchronizer.state_extractor = value
        if getattr(self, "strategic_coordinator", None) is not None:
            self.strategic_coordinator.state_extractor = value

    @property
    def strategist(self) -> Optional[Any]:
        return getattr(self.strategic_coordinator, "strategist", None)

    def reset_state(self) -> None:
        """Resets counters and collaborators for a new session or map."""
        self.mfd_processor.reset()
        self.hardware_actuator.reset()
        self.action_supervisor.reset()
        self.online_pae_trainer.reset()
        self.strategic_coordinator.reset()
        if self.guardian_shadow_trainer is not None:
            self.guardian_shadow_trainer.reset()

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
        self._last_fleet_mean_reward = 0.0

    def set_strategist(self, strategist: Optional[Any]) -> None:
        """Configures the global ST-GATv2 Strategist agent for HFT network coordination."""
        self.strategic_coordinator.set_strategist(strategist)

    def set_current_phases(self, phases: Dict[str, Any]) -> None:
        """Sets the current traffic light phase states."""
        self.current_stages = phases

    def set_guardians(self, guardians: Dict[str, Any]) -> None:
        """Configures safety guardian instances for each junction."""
        self.guardians = guardians
        if self.cycle_manager is not None and hasattr(self.cycle_manager, "set_guardians"):
            self.cycle_manager.set_guardians(guardians)

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

        # 1.5 Closed-loop hardware telemetry ingestion, EVP snapshot sync & stage reconciliation
        hardware_status = self.hardware_synchronizer.sync(traffic_data, agents, sim_time, self.current_stages)

        # 2. Safety Stage Transitions
        self.stage_transition_manager.auto_advance_transitions(sim_time, self.current_stages)
        if self.log_step_progress:
            SystemReporter.report_step_start(self.lm, self.step_counter, sim_time, "AUTOMATIC")

        # 2.5 Global ST-GATv2 Strategic Coordination
        self.strategic_coordinator.update_and_distribute(
            traffic_data=traffic_data,
            agents=agents,
            sim_time=sim_time,
            current_stages=self.current_stages,
            fleet_mean_reward=self._last_fleet_mean_reward,
        )

        # 3. Fleet Agent Evaluation
        if isinstance(getattr(self.agent_evaluator, "log_decisions", None), bool):
            self.agent_evaluator.log_decisions = bool(self.log_step_progress)
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
            self.stage_transition_manager.apply_software_transitions(decisions.actions, sim_time, self.current_stages)

        # 5. Online Continuous PAE Training & CHILD-only Guardian Shadow Observation
        self.online_pae_trainer.train_step(sim_time, agents)
        if self.guardian_shadow_trainer is not None and self.guardians:
            pae_mse = getattr(self.online_pae_trainer, "last_prediction_mse", None)
            self.guardian_shadow_trainer.observe_step(
                traffic_data, agents, self.guardians, self.current_stages, self.maturity_manager, sim_time, pae_mse
            )

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

        # 10. Outbound Telemetry Dispatch (omit raw `edges_data`: controller already holds road frame)
        publish_kwargs: Dict[str, Any] = {
            "sim_time": sim_time,
            "edges_data": {},
            "current_stages": self.current_stages,
            "tls_lanes_state": decisions.lanes_state,
            "maturity_info": decisions.maturity_info,
            "mfd_data": mfd_data,
        }
        if hardware_status:
            publish_kwargs["hardware_status"] = hardware_status
        self.telemetry_publisher.publish(**publish_kwargs)

    # --- Private Orchestration Bookkeeping ---

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
