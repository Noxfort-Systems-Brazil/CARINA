# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import os
from typing import Any, Dict, List, Optional, Set, Tuple

import sumolib
import torch
import torch.optim as optim

from src.models.st_gatv2_lite import GATv2Lite, STGATv2Lite
from src.utils.sumo_graph_loader import SumoGraphTopologyLoader


class StrategistAgent:
    """
    The Strategist Agent (Global) utilizes a GATv2 (Graph Attention Network)
    to analyze the network topology and generate context vectors (latents)
    to coordinate Local Agents.

    It autonomously parses SUMO network files to build the graph topology
    using a traversal algorithm to handle intermediate geometry nodes.
    """

    def __init__(
        self,
        input_dim: int,
        hidden_dim: int,
        output_dim: int,
        heads: int = 4,
        edge_dim: Optional[int] = 3,
        lr: float = 0.001,
        device: str = "cuda" if torch.cuda.is_available() else "cpu",
        map_path: Optional[str] = None,
        locale_manager=None,
    ):
        """
        Initializes the Strategist Agent and builds the static graph from the SUMO net file.
        """
        if map_path is None:
            from src.utils.paths import get_base_output_dir

            map_path = os.path.join(
                get_base_output_dir(), "results", "hft_live_session", "maps", "hft_live_session.net.xml"
            )
        self.device = torch.device(device)
        self.logger = logging.getLogger(__name__)
        self.locale_manager = locale_manager

        # Initialize GAT model
        self.model = GATv2Lite(input_dim, hidden_dim, output_dim, heads=heads, edge_dim=edge_dim).to(self.device)
        self.optimizer = optim.Adam(self.model.parameters(), lr=lr)

        # Topology storage
        self.edge_index: Optional[torch.Tensor] = None
        self.edge_attr: Optional[torch.Tensor] = None
        self.tls_id_to_idx: Dict[str, int] = {}
        self.idx_to_tls_id: Dict[int, str] = {}
        self.num_nodes = 0

        # Build graph from file immediately upon instantiation
        self._build_topology_from_sumo(map_path)

    def to(self, device: Any) -> "StrategistAgent":
        """Transfers the model, optimizer tensors, and topology to the target device."""
        self.device = torch.device(device)
        self.model.to(self.device)
        if self.edge_index is not None:
            self.edge_index = self.edge_index.to(self.device)
        if self.edge_attr is not None:
            self.edge_attr = self.edge_attr.to(self.device)
        return self

    def eval(self) -> "StrategistAgent":
        """Sets internal model to evaluation mode."""
        self.model.eval()
        return self

    def train(self, mode: bool = True) -> "StrategistAgent":
        """Sets internal model to training mode."""
        self.model.train(mode)
        return self

    def __call__(
        self,
        node_features: torch.Tensor,
        edge_index: Optional[torch.Tensor] = None,
        edge_attr: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """Enables direct invocation of StrategistAgent as a callable."""
        return self.get_strategic_vectors(node_features, edge_index=edge_index, edge_attr=edge_attr)

    def _get_string(self, key: str, default: str = None, **kwargs) -> str:
        if self.locale_manager and hasattr(self.locale_manager, "get_string"):
            return self.locale_manager.get_string(key, default=default, **kwargs)
        return default.format(**kwargs) if default and kwargs else (default or key)

    def _build_topology_from_sumo(self, net_file: str) -> None:
        """
        Parses the SUMO .net.xml file to extract traffic lights as nodes
        and physical connections as edges using SumoGraphTopologyLoader.
        """
        loader = SumoGraphTopologyLoader(locale_manager=self.locale_manager, logger=self.logger)
        topology_result = loader.load_topology(net_file=net_file, device=self.device)
        if len(topology_result) == 5:
            self.tls_id_to_idx, self.idx_to_tls_id, self.num_nodes, self.edge_index, self.edge_attr = topology_result
        else:
            self.tls_id_to_idx, self.idx_to_tls_id, self.num_nodes, self.edge_index = topology_result
            self.edge_attr = None

    def get_strategic_vectors(
        self,
        node_features: torch.Tensor,
        edge_index: Optional[torch.Tensor] = None,
        edge_attr: Optional[torch.Tensor] = None,
        return_prediction: bool = False,
    ) -> Any:
        """
        Executes the GAT to obtain strategic vectors, supporting 2D and 3D temporal features,
        edge attributes, and optional self-supervised future prediction.
        """
        self.model.eval()
        graph_edges = edge_index if edge_index is not None else self.edge_index
        graph_attrs = edge_attr if edge_attr is not None else self.edge_attr

        if graph_edges is None:
            raise RuntimeError(
                self._get_string(
                    "strategist_agent.topology_not_init", default="Strategist Agent: Graph topology not initialized."
                )
            )

        device_type = self.device.type
        with torch.no_grad(), torch.amp.autocast(device_type=device_type, enabled=(device_type == "cuda")):
            x = node_features.to(self.device)
            edges = graph_edges.to(self.device)
            attrs = graph_attrs.to(self.device) if graph_attrs is not None else None
            try:
                strategic_vectors = self.model(
                    x, edges, edge_attr=attrs, return_prediction=return_prediction
                )
            except TypeError:
                # Handle cases where self.model is mocked without new kwargs
                try:
                    strategic_vectors = self.model(x, edges)
                except TypeError:
                    strategic_vectors = self.model(x)

        return strategic_vectors

    def update(self, loss: torch.Tensor) -> float:
        self.model.train()
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
        self.optimizer.step()
        return float(loss.item())

    def save_checkpoint(self, path: str) -> None:
        torch.save(self.model.state_dict(), path)
        self.logger.info(
            self._get_string(
                "strategist_agent.checkpoint_saved", default="Strategist Agent checkpoint saved to {path}", path=path
            )
        )

    def load_checkpoint(self, path: str) -> None:
        if os.path.exists(path):
            try:
                state_dict = torch.load(path, map_location=self.device, weights_only=True)
            except Exception:
                state_dict = torch.load(path, map_location=self.device, weights_only=False)
            self.model.load_state_dict(state_dict)
            self.logger.info(
                self._get_string(
                    "strategist_agent.checkpoint_loaded",
                    default="Strategist Agent checkpoint loaded from {path}",
                    path=path,
                )
            )
        else:
            self.logger.warning(
                self._get_string(
                    "strategist_agent.checkpoint_not_found", default="Checkpoint not found at {path}", path=path
                )
            )

    def get_node_index(self, tls_id: str) -> int:
        return self.tls_id_to_idx.get(tls_id, -1)
