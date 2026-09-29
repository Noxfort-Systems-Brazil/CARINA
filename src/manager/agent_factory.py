# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Noxfort Systems
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

# File: src/manager/agent_factory.py
# Author: Gabriel Moraes
# Date: September 2026

import logging
from typing import Any, Dict, Optional

import torch

from agents.guardian_agent import GuardianAgent
from agents.strategist_agent import StrategistAgent
from models.pae import PredictiveAutoencoder
from src.utils.locale_manager_backend import LocaleManagerBackend


class AgentFactory:
    """Factory responsible for instantiating AI agents and autoencoder physics engines."""

    @classmethod
    def create_pae(cls, settings: Any, device: torch.device, input_dim: Optional[int] = None) -> PredictiveAutoencoder:
        """Instantiates a PredictiveAutoencoder with configurations from settings."""
        dim = input_dim or settings.getint("PAE", "input_dim", fallback=80)
        latent_dim = settings.getint("PAE", "latent_dim", fallback=16)
        lr = settings.getfloat("PAE", "learning_rate", fallback=5e-4)
        history_len = 16 if input_dim is not None else 8
        pae = PredictiveAutoencoder(input_dim=dim, latent_dim=latent_dim, lr=lr, history_len=history_len).to(device)
        return pae

    @classmethod
    def create_strategist(cls, settings: Any, map_path: str, device: torch.device) -> Optional[StrategistAgent]:
        """Instantiates the Global Strategist Agent based on system settings."""
        try:
            input_dim = settings.getint("MODEL", "input_dim", fallback=32)
            hidden_dim = settings.getint("MODEL", "hidden_dim", fallback=64)
            output_dim = settings.getint("MODEL", "output_dim", fallback=16)

            logging.info("[AgentFactory] Instantiating Strategist Agent...")
            return StrategistAgent(
                input_dim=input_dim,
                hidden_dim=hidden_dim,
                output_dim=output_dim,
                map_path=map_path,
                device=str(device),
            )
        except Exception as e:
            logging.error(f"[AgentFactory] Failed to create Strategist Agent: {e}", exc_info=True)
            return None

    @classmethod
    def create_guardians(
        cls, settings: Any, agents: Dict[str, Any], shared_pae: Any, lm: Optional[Any] = None
    ) -> Dict[str, GuardianAgent]:
        """Instantiates GuardianAgent instances for each traffic light agent."""
        guardians = {}
        guardian_config = settings["GUARDIAN_AGENT"] if "GUARDIAN_AGENT" in settings else {}
        traffic_rules_config = settings["TRAFFIC_RULES"] if "TRAFFIC_RULES" in settings else guardian_config
        locale_mgr = lm or LocaleManagerBackend()

        for tl_id, agent in agents.items():
            guardians[tl_id] = GuardianAgent(
                aiconfig=guardian_config,
                traffic_rules_config=traffic_rules_config,
                locale_manager=locale_mgr,
                shared_pae=shared_pae,
                n_observations=agent.n_observations,
            )
        return guardians
