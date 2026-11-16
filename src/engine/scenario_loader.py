# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import os
from typing import Any, Dict, Optional


class ScenarioLoader:
    """
    Use Case Coordinator responsible for loading traffic scenarios and maps,
    resetting session step states, provisioning multi-agent populations,
    and synchronizing MFD network topology.
    """

    def __init__(
        self,
        step_processor: Any,
        agent_manager: Any,
        topology_manager: Any,
        state_extractor: Any,
        maturity_manager: Any,
        mfd: Any,
        cycle_manager: Any,
        mfd_processor: Any = None,
    ) -> None:
        self.step_processor = step_processor
        self.agent_manager = agent_manager
        self.topology_manager = topology_manager
        self.state_extractor = state_extractor
        self.maturity_manager = maturity_manager
        self.mfd = mfd
        self.cycle_manager = cycle_manager
        self.mfd_processor = mfd_processor

        # Scenario Runtime State
        self.current_map_path: Optional[str] = None
        self.agents: Dict[str, Any] = {}
        self.strategist: Optional[Any] = None
        self.guardians: Dict[str, Any] = {}

    def load_scenario(self, map_path: str) -> None:
        """
        Coordinates the entire scenario bootstrapping sequence when a new
        network map geometry arrives over the control channel.
        """
        self.current_map_path = map_path
        self.agents.clear()

        # 1. Reset step processor for clean session
        self.step_processor.reset_state()

        try:
            # 2. Setup multi-agent population & environment
            self.agents, current_stages, self.strategist, self.guardians = self.agent_manager.setup_environment(
                map_path=map_path,
                topology_manager=self.topology_manager,
                state_extractor=self.state_extractor,
                maturity_manager=self.maturity_manager,
            )

            # 3. Synchronize initial phases, guardians, and arterial ST-GATv2 strategist
            self.step_processor.set_current_phases(current_stages)
            if hasattr(self.step_processor, "set_guardians"):
                self.step_processor.set_guardians(self.guardians)
            if hasattr(self.cycle_manager, "set_guardians"):
                self.cycle_manager.set_guardians(self.guardians)
            if hasattr(self.step_processor, "set_strategist"):
                self.step_processor.set_strategist(self.strategist)

            # 3.1 Dynamic Episode Steps Sizing from Graph Topology
            try:
                from src.utils.episode_step_calculator import EpisodeStepCalculator

                pacing_res = EpisodeStepCalculator.calculate(map_path)
                if hasattr(self.step_processor, "set_episode_steps"):
                    self.step_processor.set_episode_steps(pacing_res.episode_steps)
                logging.info(
                    f"[ScenarioLoader] Dynamic episode pacing calculated: "
                    f"1 episode = {pacing_res.episode_steps} steps ({pacing_res.duration_seconds:.1f}s @ 250ms/step) | "
                    f"Topology: {pacing_res.total_intersections} signals, {pacing_res.real_connections} connections, "
                    f"complexity={pacing_res.topological_complexity:.2f} | "
                    f"Inviolable 1-week safety floor = {pacing_res.child_episodes_1_week} episodes ({pacing_res.child_episodes_1_week * pacing_res.episode_steps * 0.25:.0f}s)"
                )
            except Exception as e_pacing:
                logging.warning(f"[ScenarioLoader] Dynamic episode step sizing skipped: {e_pacing}", exc_info=True)

            # 3.2 Load Synapse Peak Schedule if present
            authorizer = getattr(getattr(self.step_processor, "agent_evaluator", None), "action_authorizer", None)
            if authorizer and hasattr(authorizer, "load_peak_schedule_json"):
                for candidate in [
                    os.path.join(os.path.dirname(map_path), "peak_schedule.json"),
                    os.path.join(os.path.dirname(map_path), "..", "peak_schedule.json"),
                ]:
                    if os.path.exists(candidate):
                        try:
                            with open(candidate, "r", encoding="utf-8") as f_sched:
                                authorizer.load_peak_schedule_json(f_sched.read())
                            break
                        except Exception as e_sched:
                            logging.warning(
                                f"[ScenarioLoader] Error loading peak schedule from {candidate}: {e_sched}",
                                exc_info=True,
                            )

            # 4. Load MFD network topology
            if self.mfd and hasattr(self.mfd, "load_topology"):
                self.mfd.load_topology(map_path)

            # 5. Evaluate Cycle 0 baseline
            mfd_efficiency = 0.0
            if self.mfd_processor and hasattr(self.mfd_processor, "get_latest_efficiency"):
                mfd_efficiency = self.mfd_processor.get_latest_efficiency()
            elif self.mfd and hasattr(self.mfd, "get_latest"):
                latest = self.mfd.get_latest()
                if latest and hasattr(latest, "efficiency"):
                    mfd_efficiency = latest.efficiency

            self.cycle_manager.evaluate_cycle(0, self.agents, self.step_processor.accumulated_metrics, mfd_efficiency)

            logging.info(
                f"[ScenarioLoader] Scenario successfully loaded: {map_path} ({len(self.agents)} active agents)."
            )

        except Exception as e:
            logging.error(f"[ScenarioLoader] Failed to load scenario {map_path}: {e}", exc_info=True)
            raise
