# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# File: src/engine/step_processor.py
# Author: Gabriel Moraes
# Date: July 03, 2026

import logging
from collections import defaultdict
from typing import Any, Dict, Optional

from core.system_reporter import SystemReporter
from engine.agent_evaluator import AgentEvaluator
from engine.episode_reporter import EpisodeReporter
from engine.hardware_stage_actuator import HardwareStageActuator
from engine.stage_transition_manager import StageTransitionManager
from engine.step_timer import StepTimer
from mfd.mfd_processor import MFDProcessor
from utils.safety_rules import SafetyRules


class StepProcessor:
    """
    Responsible for managing the lifecycle and internal state of a
    Simulation/Session (Steps). Acts EXCLUSIVELY as an orchestrator.
    """

    def __init__(
        self,
        settings: Any,
        locale_manager: Any,
        agent_manager: Any,
        input_preprocessor: Any,
        state_extractor: Any,
        action_supervisor: Any,
        action_authorizer: Any,
        maturity_manager: Any,
        reward_computer: Any,
        cycle_manager: Any,
        pipe_conn: Any,
        mfd: Any = None,
        state_reconciler: Any = None,
        db_manager: Any = None,
    ) -> None:
        self.settings = settings
        self.lm = locale_manager

        self.agent_manager = agent_manager
        self.input_preprocessor = input_preprocessor
        self.state_extractor = state_extractor
        self.action_supervisor = action_supervisor
        self.action_authorizer = action_authorizer
        self.maturity_manager = maturity_manager
        self.reward_computer = reward_computer
        self.cycle_manager = cycle_manager

        self.pipe_conn = pipe_conn
        self.mfd = mfd
        self.state_reconciler = state_reconciler

        # Database Manager with Inversion of Control / Dependency Injection
        if db_manager is not None:
            self.db_manager = db_manager
        else:
            try:
                from database.database_manager import DatabaseManager

                self.db_manager = DatabaseManager(self.lm)
                self.db_manager.start_operation_session()
            except Exception as e_db:
                self.db_manager = None
                logging.warning(f"[StepProcessor] Could not initialize DatabaseManager: {e_db}")

        # Specialized SRP Collaborators
        self.step_timer = StepTimer()
        self.agent_evaluator = AgentEvaluator(
            state_extractor=self.state_extractor,
            input_preprocessor=self.input_preprocessor,
            reward_computer=self.reward_computer,
            action_authorizer=self.action_authorizer,
            action_supervisor=self.action_supervisor,
            maturity_manager=self.maturity_manager,
            locale_manager=self.lm,
            db_manager=self.db_manager,
        )
        self.stage_transition_manager = StageTransitionManager(
            state_extractor=self.state_extractor, action_supervisor=self.action_supervisor
        )
        self.episode_reporter = EpisodeReporter(locale_manager=self.lm, maturity_manager=self.maturity_manager)
        self.mfd_processor = MFDProcessor(mfd=self.mfd, state_extractor=self.state_extractor)
        self.hardware_actuator = HardwareStageActuator()

        # Session State Variables
        self.step_counter = 0
        self.start_time_offset: Optional[float] = None
        self.current_stages: Dict[str, Any] = {}
        self.accumulated_metrics = defaultdict(lambda: {"reward_sum": 0.0, "entropy_sum": 0.0, "count": 0})
        self.log_step_progress = True
        self.guardians = {}

        # --- Physical Time Transition Rules ---
        self.yellow_time = SafetyRules.get_yellow()
        self.all_red_time = SafetyRules.get_all_red()

        # --- Episode tracking ---
        self._episode_counter = 0
        self._episode_total_reward = 0.0
        self._episode_steps_in_current = 0

    @property
    def last_commanded_stages(self) -> Dict[str, int]:
        return self.hardware_actuator.last_commanded_stages

    @last_commanded_stages.setter
    def last_commanded_stages(self, val: Dict[str, int]) -> None:
        self.hardware_actuator.last_commanded_stages = val

    def reset_state(self) -> None:
        """Resets the counters for a new session (or new map)."""
        if self.mfd:
            self.mfd_processor.save_mfd_history_to_disk()
            self.mfd.reset()
        self.step_counter = 0
        self.start_time_offset = None
        self.current_stages.clear()
        self.hardware_actuator.reset()
        self.accumulated_metrics.clear()
        self.action_supervisor.reset()
        self.input_preprocessor.reset()
        self._episode_counter = 0
        self._episode_total_reward = 0.0
        self._episode_steps_in_current = 0

    def set_current_phases(self, phases: Dict[str, Any]) -> None:
        self.current_stages = phases

    def set_guardians(self, guardians: Dict[str, Any]) -> None:
        self.guardians = guardians

    def process_hft_step(self, traffic_data: Dict[str, Any], agents: Dict[str, Any]) -> None:
        """Orchestrates a single simulation step based on Real-Time Traffic Data."""
        self.step_timer.start_step()

        # Time Management
        raw_timestamp = traffic_data.get("timestamp", 0)
        if self.start_time_offset is None:
            self.start_time_offset = raw_timestamp
        sim_time = raw_timestamp - self.start_time_offset
        self.step_counter += 1
        self._episode_steps_in_current += 1

        logging.debug(
            f"[StepProcessor] Current time settings - Yellow: {self.yellow_time}s, All-Red: {self.all_red_time}s"
        )

        # Evaluate automatic physical transitions (Yellow/All-red) based on sim_time
        self.stage_transition_manager.auto_advance_transitions(sim_time, self.current_stages)

        if self.log_step_progress:
            SystemReporter.report_step_start(self.lm, self.step_counter, sim_time, "AUTOMATIC")

        actions_to_apply = {}
        edges_data = traffic_data.get("edges", {})
        tls_lanes_state = {}
        maturity_info = {}

        guardian_vetoed_any = False
        step_reward_sum = 0.0

        # --- Main Agent Loop ---
        for tl_id, agent in agents.items():
            current_stage_idx = self.current_stages.get(tl_id, 0)
            guardian = self.guardians.get(tl_id)

            action, maturity_name, vetoed, reward, entropy, lanes_state = self.agent_evaluator.evaluate_agent(
                tl_id, agent, current_stage_idx, traffic_data, edges_data, sim_time, guardian, self.step_timer
            )

            tls_lanes_state[tl_id] = lanes_state
            maturity_info[tl_id] = maturity_name
            step_reward_sum += reward
            self.accumulated_metrics[tl_id]["reward_sum"] += reward
            self.accumulated_metrics[tl_id]["entropy_sum"] += entropy
            self.accumulated_metrics[tl_id]["count"] += 1

            if vetoed:
                guardian_vetoed_any = True

            if action is not None:
                actions_to_apply[tl_id] = action

        # --- Execute Actions ---
        if actions_to_apply:
            self.action_supervisor.apply_actions(actions_to_apply, sim_time, self.current_stages)

        # --- Update Software Phases after Hardware Actions ---
        for tl_id, action in actions_to_apply.items():
            if action == 0:
                current_stage_idx = self.current_stages.get(tl_id, 0)
                self.stage_transition_manager.update_estimated_stage(
                    tl_id, current_stage_idx, sim_time, self.current_stages
                )

        self._episode_total_reward += step_reward_sum

        # Finish and log timing breakdown
        self.step_timer.log_and_finish_step(guardian_vetoed_any, self.log_step_progress)

        # Lifecycle Check (Episode Boundary)
        episode_steps = self.settings.getint("AI_TRAINING", "episode_max_steps", fallback=100)
        if self.step_counter % episode_steps == 0:
            self._episode_counter += 1

            mfd_efficiency = 0.0
            if self.mfd:
                latest = self.mfd.get_latest()
                if latest:
                    mfd_efficiency = latest.efficiency

            self.cycle_manager.evaluate_cycle(self.step_counter, agents, self.accumulated_metrics, mfd_efficiency)
            self.episode_reporter.report_episode_bulletin(agents, self._episode_counter, self._episode_total_reward)

            self._episode_total_reward = 0.0
            self._episode_steps_in_current = 0

        # MFD: Compute Network Performance
        mfd_data = self.mfd_processor.process_step(
            edges_data=edges_data,
            sim_time=sim_time,
            agents_keys=list(agents.keys()),
            step_counter=self.step_counter,
            episode_steps=episode_steps,
        )

        # Delegate hardware stage commands & logging to dedicated actuator
        self.hardware_actuator.sync_hardware_stages(
            action_supervisor=self.action_supervisor,
            current_stages=self.current_stages,
            state_extractor=self.state_extractor,
            state_reconciler=self.state_reconciler,
        )

        # Send HFT telemetry feedback to Central Controller pipe
        if self.pipe_conn:
            rich_payload = {
                "edges": edges_data,
                "tls_phases": self.current_stages,
                "tls_lanes_state": tls_lanes_state,
                "maturity": maturity_info,
                "mfd": mfd_data,
                "sim_time": sim_time,
            }
            try:
                self.pipe_conn.send(("ai_telemetry_sync", rich_payload))
            except Exception as e:
                logging.error(f"[TRAINER] Failed to send AI Telemetry update: {e}")
