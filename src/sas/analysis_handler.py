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

# File: src/sas/analysis_handler.py
# Author: Gabriel Moraes
# Date: July 08, 2026

import logging
import os
import time

from src.sas.network_file_resolver import NetworkFileResolver
from src.sas.simulation_run_resolver import SimulationRunResolver


class AnalysisHandler:
    """Handles parsing and processing of messages for the SAS service, delegating analysis tasks."""

    def __init__(self, orchestrator):
        self.orch = orchestrator

    def process_message(self, message):
        """Processes an incoming simulation data or control packet."""
        if isinstance(message, tuple):
            msg_type, payload = message
            if msg_type == "hft_rich_update":
                self.handle_hft_rich_update(payload)
            elif msg_type == "trigger_analysis":
                self.handle_trigger_analysis()
        else:
            self.handle_standard_sim_data(message)

    def handle_hft_rich_update(self, payload):
        """Processes real-time traffic updates from high-frequency traffic monitoring."""
        orch = self.orch
        orch.last_scenario_name = "hft_live_session"

        # 1. Resolve net_file_path dynamically
        net_file_path = self.resolve_net_file_path(orch.last_scenario_name)
        if not net_file_path:
            return
        orch.last_net_file_path = net_file_path

        # 2. Get or create current_run_id in DB
        if orch.current_run_id is None:
            orch.current_run_id = self.resolve_run_id(orch.last_scenario_name)

        # 3. Track simulation time for schedule check
        current_sim_time = payload.get("sim_time")
        if current_sim_time is None:
            if not hasattr(orch, "_hft_start_time"):
                orch._hft_start_time = time.time()
            current_sim_time = int(time.time() - orch._hft_start_time)
        orch.last_sim_time = current_sim_time

        is_past_initial_delay = current_sim_time >= orch.initial_delay
        is_time_for_analysis = (current_sim_time - orch.last_analysis_time) >= orch.frequency

        if is_past_initial_delay and is_time_for_analysis:
            logging.info(f"[SAS_ORCH] Triggering HFT real-time analysis at sim_time={current_sim_time}")
            try:
                calibration_data = (
                    list(orch.collector.calibration_data_points) if orch.collector.calibration_data_points else None
                )
                orch.engine.run_analysis(
                    accumulated_data=orch.collector.get_accumulated_data(),
                    sim_duration=current_sim_time,
                    scenario_name=orch.last_scenario_name,
                    net_file_path=net_file_path,
                    run_id=orch.current_run_id,
                    calibration_data_points=calibration_data,
                    db_manager=orch.db_manager,
                )
            except Exception as e:
                logging.error(f"[SAS_ORCH] Error running HFT analysis: {e}", exc_info=True)
            orch.last_analysis_time = current_sim_time
            # MEMORY FIX: Reset collector after analysis to free accumulated data
            orch.collector.reset()
            logging.info(orch.locale_manager.get_string("sas_orchestrator.run.analysis_cycle_complete"))

    def handle_trigger_analysis(self):
        """Processes manual or UI-triggered requests to generate an analysis report immediately."""
        orch = self.orch
        logging.info("[SAS_ORCH] Manual/UI trigger received. Running analysis immediately.")

        # Resolve net_file_path dynamically if needed
        if not orch.last_net_file_path:
            orch.last_net_file_path = self.resolve_net_file_path(orch.last_scenario_name)

        # Get or create current_run_id if needed
        if orch.current_run_id is None:
            orch.current_run_id = self.resolve_run_id(orch.last_scenario_name)

        if not orch.last_net_file_path:
            logging.warning("[SAS_ORCH] Cannot run manual analysis: net_file_path not available.")
            return

        # Calculate current sim_time
        if hasattr(orch, "last_sim_time") and orch.last_sim_time is not None:
            current_sim_time = orch.last_sim_time
        else:
            if not hasattr(orch, "_hft_start_time"):
                orch._hft_start_time = time.time()
            current_sim_time = int(time.time() - orch._hft_start_time)

        # Ensure we have at least 1 second to avoid duration/path invalid error
        current_sim_time = max(current_sim_time, 1)

        logging.info(
            f"[SAS_ORCH] Running triggered analysis for {orch.last_scenario_name} (run_id={orch.current_run_id})"
        )
        try:
            orch.engine.run_analysis(
                accumulated_data={},
                sim_duration=current_sim_time,
                scenario_name=orch.last_scenario_name,
                net_file_path=orch.last_net_file_path,
                run_id=orch.current_run_id,
                db_manager=orch.db_manager,
            )
            orch.last_analysis_time = current_sim_time
        except Exception as e:
            logging.error(f"[SAS_ORCH] Error running manual triggered analysis: {e}", exc_info=True)

    def handle_standard_sim_data(self, raw_sim_data):
        """Processes standard, step-by-step simulation state packets."""
        orch = self.orch
        lm = orch.locale_manager

        if orch.current_run_id is None and isinstance(raw_sim_data.get("run_id"), int):
            orch.current_run_id = raw_sim_data["run_id"]
            logging.info(lm.get_string("sas_orchestrator.run.run_id_captured", run_id=orch.current_run_id))

        if isinstance(raw_sim_data, dict):
            if "scenario_name" in raw_sim_data:
                orch.last_scenario_name = raw_sim_data["scenario_name"]
            if "net_file" in raw_sim_data:
                orch.last_net_file_path = raw_sim_data["net_file"]
                if orch.last_net_file_path and os.path.exists(orch.last_net_file_path):
                    self._save_last_known_net_file(orch.last_net_file_path)

        orch.collector.collect(raw_sim_data)

        current_sim_time = raw_sim_data.get("sim_time", 0)
        orch.last_sim_time = current_sim_time

        is_past_initial_delay = current_sim_time >= orch.initial_delay
        is_time_for_analysis = (current_sim_time - orch.last_analysis_time) >= orch.frequency

        if is_past_initial_delay and is_time_for_analysis:
            logging.info(lm.get_string("sas_orchestrator.run.analysis_triggered", time=current_sim_time))

            accumulated_data = orch.collector.get_accumulated_data()

            if accumulated_data and orch.current_run_id is not None:
                orch.engine.run_analysis(
                    accumulated_data=accumulated_data,
                    sim_duration=current_sim_time,
                    scenario_name=orch.last_scenario_name,
                    net_file_path=orch.last_net_file_path,
                    run_id=orch.current_run_id,
                    db_manager=orch.db_manager,
                )
            elif orch.current_run_id is None:
                logging.warning(lm.get_string("sas_orchestrator.run.analysis_skipped_no_run_id"))

            orch.last_analysis_time = current_sim_time
            orch.collector.reset()
            logging.info(lm.get_string("sas_orchestrator.run.analysis_cycle_complete"))

    def _save_last_known_net_file(self, path):
        """Delegates persistence to NetworkFileResolver."""
        NetworkFileResolver.save_last_known_net_file(path)

    def _load_last_known_net_file(self):
        """Delegates loading to NetworkFileResolver."""
        return NetworkFileResolver.load_last_known_net_file()

    def resolve_net_file_path(self, scenario_name):
        """Delegates resolution to NetworkFileResolver."""
        return NetworkFileResolver.resolve_net_file_path(scenario_name)

    def resolve_run_id(self, scenario_name):
        """Delegates run ID resolution to SimulationRunResolver."""
        return SimulationRunResolver.resolve_run_id(self.orch.db_manager, scenario_name)
