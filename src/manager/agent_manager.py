# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import Any, Dict, Optional, Tuple

import torch

from agents.strategist_agent import StrategistAgent
from manager.agent_checkpoint_repository import AgentCheckpointRepository
from manager.agent_factory import AgentFactory
from safety.guardian_checkpoint_service import GuardianCheckpointService

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

        max_obs_size = 0
        num_nodes = 0
        try:
            if hasattr(state_extractor, "load_topology"):
                state_extractor.load_topology(map_path)
                logging.info("[AgentManager] StateExtractor topology initialized.")

                num_nodes = len(getattr(state_extractor, "tl_incoming_edges", {}))
                for tl_id in state_extractor.tl_incoming_edges.keys():
                    obs_size = state_extractor.get_observation_space_size(tl_id)
                    if obs_size > max_obs_size:
                        max_obs_size = obs_size

                if max_obs_size > 0:
                    logging.info(
                        f"[AgentManager] Adjusting PAE input_dim dynamically from "
                        f"{self.shared_pae.input_dim} to {max_obs_size} (nodes={num_nodes})"
                    )
                    self.shared_pae = AgentFactory.create_pae(
                        self.settings, self.device, input_dim=max_obs_size, num_nodes=num_nodes
                    )
        except Exception as e:
            logging.error(f"[AgentManager] Failed to initialize StateExtractor: {e}", exc_info=True)

        # 1. Load Local Agents via Topology Manager (with PAE injection)
        agents, current_stages = topology_manager.load_topology(
            map_path, state_extractor, maturity_manager, self.shared_pae
        )

        # 2. Instantiate Strategist Agent (Global Brain) aligned to real map observation space
        if max_obs_size <= 0 and agents:
            max_obs_size = max((getattr(a, "n_observations", 0) for a in agents.values()), default=0)
        if num_nodes <= 0:
            num_nodes = len(agents)
        strategist = self._create_strategist(
            map_path, input_dim=max_obs_size if max_obs_size > 0 else None, num_nodes=num_nodes
        )

        # 3. Instantiate Guardian Agents synchronously with true topology slicing & capacities
        guardians = AgentFactory.create_guardians(
            self.settings, agents, self.shared_pae, state_extractor=state_extractor
        )

        # 4. Restore State (Load Checkpoints from map dir and active HFT session if present)
        self.restore_system_state(map_path, agents, strategist, guardians)
        GuardianCheckpointService.load_all(guardians, device=self.device)
        for tl_id, guardian in guardians.items():
            if hasattr(guardian, "configure_topology") and state_extractor is not None:
                guardian.configure_topology(
                    edge_feature_dim=(
                        state_extractor.get_edge_feature_dim(tl_id)
                        if hasattr(state_extractor, "get_edge_feature_dim")
                        else None
                    ),
                    edge_capacities=(
                        state_extractor.get_edge_capacities(tl_id)
                        if hasattr(state_extractor, "get_edge_capacities")
                        else None
                    ),
                )
            phase = (
                maturity_manager.get_agent_phase(tl_id)
                if callable(getattr(maturity_manager, "get_agent_phase", None))
                else getattr(maturity_manager, "agent_maturity", {}).get(tl_id)
            )
            if phase is not None and str(getattr(phase, "name", phase)).upper() != "CHILD":
                if callable(getattr(guardian, "freeze_for_deployment", None)):
                    guardian.freeze_for_deployment()

        return agents, current_stages, strategist, guardians

    def _create_strategist(
        self, map_path: str, input_dim: Optional[int] = None, num_nodes: int = 0
    ) -> Optional[StrategistAgent]:
        """Factory delegate method for the Strategist Agent."""
        return AgentFactory.create_strategist(
            self.settings, map_path, self.device, input_dim=input_dim, num_nodes=num_nodes
        )

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
