# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import Any, Dict, Optional

import torch

from agents.guardian_agent import GuardianAgent
from agents.strategist_agent import StrategistAgent
from models.pae import PredictiveAutoencoder
from utils.locale_manager_backend import LocaleManagerBackend
from utils.topo_scaler import TopologicalScaler


class AgentFactory:
    """Factory responsible for instantiating AI agents, ST-GATv2 strategists, and PAE world models."""

    @classmethod
    def create_pae(
        cls,
        settings: Any,
        device: torch.device,
        input_dim: Optional[int] = None,
        num_nodes: int = 0,
    ) -> PredictiveAutoencoder:
        """Instantiates the Universal Action-Conditioned PredictiveAutoencoder."""
        dim = input_dim or (settings.getint("PAE", "input_dim", fallback=80) if hasattr(settings, "getint") else 80)
        latent_dim = settings.getint("PAE", "latent_dim", fallback=16) if hasattr(settings, "getint") else 16
        seq_len = settings.getint("AI_TRAINING", "sequence_length", fallback=12) if hasattr(settings, "getint") else 12
        history_len = max(12, int(seq_len)) if input_dim is not None else max(8, int(seq_len))
        nhead = TopologicalScaler.calculate_num_heads(num_nodes) if num_nodes > 0 else 4
        d_model = max(32, nhead * 8)

        pae = PredictiveAutoencoder(
            input_dim=dim,
            latent_dim=latent_dim,
            history_len=history_len,
            d_model=d_model,
            nhead=nhead,
            n_actions=2,
        ).to(device)

        enable_compile = (
            settings.getboolean("PAE", "enable_torch_compile", fallback=False)
            if hasattr(settings, "getboolean")
            else False
        )
        if enable_compile and hasattr(device, "type") and device.type == "cuda":
            pae.optimize_engine(enable_compile=True)

        return pae

    @classmethod
    def create_strategist(
        cls,
        settings: Any,
        map_path: str,
        device: torch.device,
        input_dim: Optional[int] = None,
        num_nodes: int = 0,
    ) -> Optional[StrategistAgent]:
        """Instantiates the Global ST-GATv2 Strategist Agent with dynamic observation & topological scaling."""
        try:
            resolved_input_dim = input_dim or (
                settings.getint("GAT_STRATEGIST", "input_dim", fallback=0) if hasattr(settings, "getint") else 0
            )
            if not resolved_input_dim or resolved_input_dim <= 0:
                resolved_input_dim = (
                    settings.getint("MODEL", "input_dim", fallback=32) if hasattr(settings, "getint") else 32
                )

            hidden_dim = (
                settings.getint("GAT_STRATEGIST", "hidden_dim", fallback=64) if hasattr(settings, "getint") else 64
            )
            output_dim = (
                settings.getint("GAT_STRATEGIST", "output_dim", fallback=8) if hasattr(settings, "getint") else 8
            )
            default_heads = TopologicalScaler.calculate_num_heads(num_nodes) if num_nodes > 0 else 4
            heads = (
                settings.getint("GAT_STRATEGIST", "heads", fallback=default_heads)
                if hasattr(settings, "getint")
                else default_heads
            )

            logging.info(
                f"[AgentFactory] Instantiating ST-GATv2 Strategist Agent "
                f"(input_dim={resolved_input_dim}, hidden_dim={hidden_dim}, output_dim={output_dim}, heads={heads})..."
            )
            return StrategistAgent(
                input_dim=resolved_input_dim,
                hidden_dim=hidden_dim,
                output_dim=output_dim,
                heads=heads,
                map_path=map_path,
                device=str(device),
            )
        except Exception as e:
            logging.error(f"[AgentFactory] Failed to create Strategist Agent: {e}", exc_info=True)
            return None

    @classmethod
    def create_guardians(
        cls,
        settings: Any,
        agents: Dict[str, Any],
        shared_pae: Any,
        lm: Optional[Any] = None,
        state_extractor: Optional[Any] = None,
    ) -> Dict[str, GuardianAgent]:
        """Instantiates Distributional QR-D3QN GuardianAgent instances for each traffic light."""
        guardians = {}
        guardian_config = settings["GUARDIAN_AGENT"] if "GUARDIAN_AGENT" in settings else {}
        traffic_rules_config = settings["TRAFFIC_RULES"] if "TRAFFIC_RULES" in settings else guardian_config
        locale_mgr = lm or LocaleManagerBackend()

        for tl_id, agent in agents.items():
            edge_dim = (
                state_extractor.get_edge_feature_dim(tl_id)
                if state_extractor is not None and hasattr(state_extractor, "get_edge_feature_dim")
                else None
            )
            edge_caps = (
                state_extractor.get_edge_capacities(tl_id)
                if state_extractor is not None and hasattr(state_extractor, "get_edge_capacities")
                else None
            )
            guardians[tl_id] = GuardianAgent(
                aiconfig=guardian_config,
                traffic_rules_config=traffic_rules_config,
                locale_manager=locale_mgr,
                shared_pae=shared_pae,
                n_observations=agent.n_observations,
                edge_feature_dim=edge_dim,
                edge_capacities=edge_caps,
            )
        return guardians
