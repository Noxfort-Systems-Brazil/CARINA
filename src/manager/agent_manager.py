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

import os
import logging
import torch
from typing import Dict, Any, Tuple, Optional

# Import Strategist (Global Agent)
from agents.strategist_agent import StrategistAgent

class AgentManager:
    """
    Manages the lifecycle (creation, persistence, restoration) of AI Agents.
    This component relieves the main Trainer/Orchestrator from file I/O operations
    and instantiation logic.
    """

    def __init__(self, settings: Any, device: torch.device, project_root: str):
        """
        Args:
            settings: ConfigParser object containing system settings.
            device: Torch device (CPU/CUDA).
            project_root: Base path of the project for saving results.
        """
        self.settings = settings
        self.device = device
        self.project_root = project_root

    def setup_environment(self, map_path: str, topology_manager: Any, 
                         state_extractor: Any, maturity_manager: Any) -> Tuple[Dict[str, Any], Dict[str, int], Optional[StrategistAgent]]:
        """
        Orchestrates the creation of the AI environment for a specific map.
        
        1. Delegates local agent creation to TopologyManager.
        2. Instantiates the Global Strategist Agent.
        3. Attempts to restore previous checkpoints.

        Args:
            map_path: Path to the .net.xml file.
            topology_manager: Instance of TopologyManager to parse the map.
            state_extractor: Instance of StateExtractor.
            maturity_manager: Instance of MaturityManager.

        Returns:
            Tuple containing:
            - agents (Dict): Map of 'tl_id' to LocalAgent instances.
            - current_phases (Dict): Initial phase indices for each traffic light.
            - strategist (StrategistAgent): The global network controller (or None).
        """
        logging.info(f"[AgentManager] Setting up environment for map: {map_path}")
        
        # --- FIX: Explicitly initialize StateExtractor with the map topology ---
        # This ensures that get_phase_lane_states() works for the UI and
        # get_observation_space_size() works for Agent creation.
        try:
            if hasattr(state_extractor, 'load_topology'):
                state_extractor.load_topology(map_path)
                logging.info("[AgentManager] StateExtractor topology initialized.")
        except Exception as e:
            logging.error(f"[AgentManager] Failed to initialize StateExtractor: {e}", exc_info=True)
        # -----------------------------------------------------------------------

        # 1. Load Local Agents via Topology Manager
        # TopologyManager handles the map parsing and local agent factory logic.
        agents, current_phases = topology_manager.load_topology(
            map_path, state_extractor, maturity_manager
        )
        
        # 2. Instantiate Strategist Agent (Global Brain)
        strategist = self._create_strategist(map_path)
        
        # 3. Restore State (Load Checkpoints)
        self.restore_system_state(map_path, agents, strategist)
        
        return agents, current_phases, strategist

    def _create_strategist(self, map_path: str) -> Optional[StrategistAgent]:
        """
        Factory method for the Strategist Agent based on settings.
        """
        try:
            input_dim = self.settings.getint('MODEL', 'input_dim', fallback=32)
            hidden_dim = self.settings.getint('MODEL', 'hidden_dim', fallback=64)
            output_dim = self.settings.getint('MODEL', 'output_dim', fallback=16)
            
            logging.info(f"[AgentManager] Instantiating Strategist Agent...")
            return StrategistAgent(
                input_dim=input_dim,
                hidden_dim=hidden_dim,
                output_dim=output_dim,
                map_path=map_path,
                device=str(self.device)
            )
        except Exception as e:
            logging.error(f"[AgentManager] Failed to create Strategist Agent: {e}", exc_info=True)
            return None

    def save_system_state(self, map_path: str, agents: Dict[str, Any], strategist: Optional[StrategistAgent]):
        """
        Persists the state (weights) of all agents to disk.
        
        Args:
            map_path: The current map file path (used to derive folder name).
            agents: Dictionary of local agents.
            strategist: The global strategist instance.
        """
        if not map_path:
            logging.warning("[AgentManager] Cannot save state: No map path provided.")
            return

        # Derive Checkpoint Directory: results/{map_name}/checkpoints
        map_name = os.path.basename(map_path).replace('.net.xml', '')
        from src.utils.paths import get_base_output_dir
        ckpt_dir = os.path.join(get_base_output_dir(), 'results', map_name, 'checkpoints')
        os.makedirs(ckpt_dir, exist_ok=True)

        count_saved = 0
        
        # Save Local Agents
        for tl_id, agent in agents.items():
            try:
                # Sanitize ID for filename (replace colons/slashes)
                safe_id = tl_id.replace(":", "_").replace("/", "_")
                path = os.path.join(ckpt_dir, f"agent_{safe_id}.pth")
                
                if hasattr(agent, 'save'):
                    agent.save(path)
                    count_saved += 1
            except Exception as e:
                logging.error(f"[AgentManager] Failed to save agent {tl_id}: {e}")

        # Save Strategist
        if strategist:
            try:
                strat_path = os.path.join(ckpt_dir, "strategist_global.pth")
                strategist.save_checkpoint(strat_path)
                logging.info(f"[AgentManager] Strategist state saved.")
            except Exception as e:
                logging.error(f"[AgentManager] Failed to save Strategist: {e}")

        logging.info(f"[AgentManager] System state saved to {ckpt_dir} ({count_saved} local agents).")

    def restore_system_state(self, map_path: str, agents: Dict[str, Any], strategist: Optional[StrategistAgent]):
        """
        Loads the state (weights) of agents from disk if available.
        """
        if not map_path:
            return

        map_name = os.path.basename(map_path).replace('.net.xml', '')
        from src.utils.paths import get_base_output_dir
        ckpt_dir = os.path.join(get_base_output_dir(), 'results', map_name, 'checkpoints')

        if not os.path.exists(ckpt_dir):
            logging.info("[AgentManager] No checkpoints found. Starting with fresh agents.")
            return

        # Load Local Agents
        for tl_id, agent in agents.items():
            safe_id = tl_id.replace(":", "_").replace("/", "_")
            path = os.path.join(ckpt_dir, f"agent_{safe_id}.pth")
            
            if os.path.exists(path):
                try:
                    if hasattr(agent, 'load'):
                        agent.load(path)
                except Exception as e:
                    logging.warning(f"[AgentManager] Failed to load checkpoint for {tl_id}: {e}")

        # Load Strategist
        if strategist:
            strat_path = os.path.join(ckpt_dir, "strategist_global.pth")
            if os.path.exists(strat_path):
                try:
                    strategist.load_checkpoint(strat_path)
                    logging.info(f"[AgentManager] Strategist state restored.")
                except Exception as e:
                     logging.warning(f"[AgentManager] Failed to load Strategist checkpoint: {e}")