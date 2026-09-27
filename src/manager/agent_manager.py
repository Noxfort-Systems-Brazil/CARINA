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

# File: src/manager/agent_manager.py
# Author: Gabriel Moraes
# Date: February 19, 2026

import logging
from typing import Any, Dict, Optional, Tuple

import torch

from agents.strategist_agent import StrategistAgent
from src.manager.agent_checkpoint_repository import AgentCheckpointRepository
from src.manager.agent_factory import AgentFactory

# Re-exports for backward compatibility
__all__ = ["AgentManager", "AgentFactory", "AgentCheckpointRepository"]


class AgentManager:
    """
    Manages the lifecycle (creation, persistence, restoration) of AI Agents.
    Acts as high-level coordinator delegating instantiation to AgentFactory
    and state persistence to AgentCheckpointRepository.
    """

    def __init__(self, settings: Any, device: torch.device, project_root: str):
        self.settings = settings
        self.device = device
        self.project_root = project_root

        # --- Universal PAE (Shared Physics Engine) ---
        self.shared_pae = AgentFactory.create_pae(settings, device)
        logging.info(
            f"[AgentManager] Universal PAE instantiated "
            f"(input={self.shared_pae.input_dim}, latent={self.shared_pae.latent_dim})"
        )

    def setup_environment(
        self,
        map_path: str,
        topology_manager: Any,
        state_extractor: Any,
        maturity_manager: Any,
    ) -> Tuple[Dict[str, Any], Dict[str, int], Optional[StrategistAgent], Dict[str, Any]]:
        """Orchestrates the creation and initialization of the AI environment for a specific map."""
        logging.info(f"[AgentManager] Setting up environment for map: {map_path}")

        # Initialize StateExtractor with map topology if supported
        try:
            if hasattr(state_extractor, "load_topology"):
                state_extractor.load_topology(map_path)
                logging.info("[AgentManager] StateExtractor topology initialized.")

                # Re-initialize PAE dynamically with correct augmented dimension
                max_obs_size = 0
                for tl_id in state_extractor.tl_incoming_edges.keys():
                    obs_size = state_extractor.get_observation_space_size(tl_id)
                    if obs_size > max_obs_size:
                        max_obs_size = obs_size

                if max_obs_size > 0:
                    logging.info(
                        f"[AgentManager] Adjusting PAE input_dim dynamically from "
                        f"{self.shared_pae.input_dim} to {max_obs_size}"
                    )
                    self.shared_pae = AgentFactory.create_pae(self.settings, self.device, input_dim=max_obs_size)
        except Exception as e:
            logging.error(f"[AgentManager] Failed to initialize StateExtractor: {e}", exc_info=True)

        # 1. Load Local Agents via Topology Manager (with PAE injection)
        agents, current_stages = topology_manager.load_topology(
            map_path, state_extractor, maturity_manager, self.shared_pae
        )

        # 2. Instantiate Strategist Agent (Global Brain)
        strategist = self._create_strategist(map_path)

        # 3. Instantiate Guardian Agents synchronously
        guardians = AgentFactory.create_guardians(self.settings, agents, self.shared_pae)

        # 4. Restore State (Load Checkpoints)
        self.restore_system_state(map_path, agents, strategist, guardians)

        return agents, current_stages, strategist, guardians

    def _create_strategist(self, map_path: str) -> Optional[StrategistAgent]:
        """Factory delegate method for the Strategist Agent."""
        return AgentFactory.create_strategist(self.settings, map_path, self.device)

    def save_system_state(
        self,
        map_path: str,
        agents: Dict[str, Any],
        strategist: Optional[StrategistAgent],
        guardians: Optional[Dict[str, Any]] = None,
    ):
        """Persists the state of all agents to disk via AgentCheckpointRepository."""
        AgentCheckpointRepository.save_system_state(
            map_path=map_path,
            agents=agents,
            strategist=strategist,
            shared_pae=self.shared_pae,
            guardians=guardians,
        )

    def restore_system_state(
        self,
        map_path: str,
        agents: Dict[str, Any],
        strategist: Optional[StrategistAgent],
        guardians: Optional[Dict[str, Any]] = None,
    ):
        """Restores the state of agents from disk via AgentCheckpointRepository."""
        AgentCheckpointRepository.restore_system_state(
            map_path=map_path,
            agents=agents,
            strategist=strategist,
            shared_pae=self.shared_pae,
            guardians=guardians,
            device=self.device,
        )
