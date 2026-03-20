# File: src/xai/agent_reconstructor.py
# Author: Gabriel Moraes
# Date: December 17, 2025

import os
import torch
import logging

from agents.local_agent import LocalAgent
from utils.locale_manager_backend import LocaleManagerBackend

class AgentReconstructor:
    """
    Responsibility: Load physical PyTorch Checkpoints (.pth) from the disk,
    validate their structure, and instantiate 'Blind' LocalAgents (disconnected 
    from the live SUMO/Synapse network) strictly for Mathematical Analysis.
    """

    def __init__(self, checkpoints_dir: str):
        self.checkpoints_dir = checkpoints_dir
        self.locale_manager = LocaleManagerBackend()
        
    def reconstruct_agent(self, agent_id: str) -> LocalAgent:
        """Loads weights from disk and reconstructs the Agent memory."""
        checkpoint_path = os.path.join(self.checkpoints_dir, f"agent_{agent_id}.pth")
        
        if not os.path.exists(checkpoint_path):
            raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")

        # Load with safe weights_only=False (required for complex agent dicts)
        try:
            checkpoint = torch.load(checkpoint_path, map_location=torch.device('cpu'), weights_only=False)
        except Exception as e:
            raise RuntimeError(f"Corrupted checkpoint for {agent_id}: {e}")
            
        n_observations = checkpoint.get('n_observations')
        
        if n_observations is None:
            raise ValueError(f"Invalid checkpoint structure for {agent_id}. Missing 'n_observations'.")

        # Reconstruct Agent (Blind Mode - No Synapse Connection)
        agent = LocalAgent(
            tlight_id=agent_id,
            n_observations=n_observations,
            n_actions=3, 
            initial_hyperparams={},
            log_dir="",
            locale_manager=self.locale_manager 
        )
        
        agent.load_checkpoint(checkpoint_path)
        logging.info(f"[AgentReconstructor] Successfully loaded blind agent for {agent_id}.")
        return agent
