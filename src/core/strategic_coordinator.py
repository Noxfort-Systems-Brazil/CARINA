# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import torch

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

from agents.strategist_agent import StrategistAgent
from core.structural_graph_builder import StructuralGraphBuilder
from core.temporal_sequence_manager import TemporalSequenceManager


class StrategicCoordinator:
    """Manages the lifecycle and execution of the GAT Strategist."""

    def __init__(
        self,
        settings: Any,
        device: Any,
        locale_manager: "LocaleManagerBackend",
        shared_pae: Optional[Any] = None,
    ):
        self.settings = settings
        self.device = torch.device(device) if isinstance(device, str) else device
        self.locale_manager = locale_manager
        self.shared_pae = shared_pae
        lm = self.locale_manager

        gat_settings = settings["GAT_STRATEGIST"]
        if hasattr(gat_settings, "getint"):
            self.update_frequency = gat_settings.getint("update_frequency_seconds")
            self.output_dim = gat_settings.getint("output_dim")
        else:
            self.update_frequency = int(gat_settings.get("update_frequency_seconds", 5))
            self.output_dim = int(gat_settings.get("output_dim", 8))

        try:
            temporal_window = (
                gat_settings.getint("temporal_window")
                if hasattr(gat_settings, "getint")
                else int(gat_settings.get("temporal_window", 12))
            )
        except Exception:
            temporal_window = 12

        self.temporal_window = temporal_window
        self.sequence_manager = TemporalSequenceManager(temporal_window=self.temporal_window)

        self.gat_model: Optional[StrategistAgent] = None
        self.last_update_time = -self.update_frequency
        self.strategic_vectors = None
        self.graph_edge_index = None
        self.graph_edge_attr = None

        self.tl_id_to_idx: Dict[str, int] = {}
        self.tl_idx_to_id: Dict[int, str] = {}
        self.max_state_dim = 0
        logging.info(lm.get_string("strategic_coordinator.init.created"))

    @property
    def temporal_buffer(self):
        return self.sequence_manager.temporal_buffer

    @property
    def prediction_target_time(self):
        return self.sequence_manager.prediction_target_time

    @property
    def cached_future_pred(self):
        return self.sequence_manager.cached_future_pred

    def initialize(self, traci_conn: Any):
        """Constructs network graph topology, initializes the GAT model, and returns metric dimensions."""
        lm = self.locale_manager
        logging.info(lm.get_string("strategic_coordinator.initialize.start"))

        graph_res = StructuralGraphBuilder.build_network_graph(traci_conn, self.device, lm)
        if len(graph_res) == 7:
            (
                self.graph_edge_index,
                self.max_state_dim,
                self.tl_id_to_idx,
                self.tl_idx_to_id,
                num_nodes,
                num_edges,
                self.graph_edge_attr,
            ) = graph_res
        else:
            (
                self.graph_edge_index,
                self.max_state_dim,
                self.tl_id_to_idx,
                self.tl_idx_to_id,
                num_nodes,
                num_edges,
            ) = graph_res
            self.graph_edge_attr = None

        gat_settings = self.settings["GAT_STRATEGIST"]
        try:
            edge_dim = gat_settings.getint("edge_dim")
        except Exception:
            edge_dim = 3

        self.gat_model = StrategistAgent(
            input_dim=self.max_state_dim,
            hidden_dim=gat_settings.getint("hidden_dim"),
            output_dim=self.output_dim,
            heads=gat_settings.getint("heads"),
            edge_dim=edge_dim,
            device=str(self.device),
        ).to(self.device)
        logging.info(lm.get_string("strategic_coordinator.initialize.model_created", device=self.device))

        num_agents = len(self.tl_id_to_idx)
        self.strategic_vectors = torch.zeros((num_agents, self.output_dim), device=self.device)
        return self.max_state_dim, num_nodes, num_edges

    def update_if_needed(self, sim_time: float, current_states_dict: Dict[str, Any]):
        """Checks if it is time to execute the GAT and updates strategic vectors."""
        lm = self.locale_manager
        if self.gat_model is None or self.graph_edge_index is None:
            if self.graph_edge_index is None and self.gat_model is not None:
                logging.warning(
                    lm.get_string(
                        "strategic_coordinator.update.edge_index_not_init",
                        default="[StrategicCoordinator] graph_edge_index not initialized. Skipping update.",
                    )
                )
            return

        if (sim_time - self.last_update_time) < self.update_frequency:
            return

        logging.info(
            lm.get_string(
                "strategic_coordinator.update.running",
                default="[STRATEGIC_COORD] Running GAT update at time {time}s",
                time=sim_time,
            )
        )

        num_agents = len(self.tl_id_to_idx)
        node_features, valid_agent_indices = StructuralGraphBuilder.extract_padded_features(
            current_states_dict=current_states_dict,
            tl_idx_to_id=self.tl_idx_to_id,
            num_agents=num_agents,
            max_state_dim=self.max_state_dim,
            sim_time=sim_time,
            lm=lm,
        )

        if not node_features:
            logging.warning(
                lm.get_string(
                    "strategic_coordinator.update.no_valid_features",
                    default="No valid node features to process at time {time}.",
                    time=sim_time,
                )
            )
            return

        node_features_tensor = torch.tensor(node_features, dtype=torch.float32).to(self.device)

        # 1. Self-supervised prediction training
        self.sequence_manager.evaluate_and_train_prediction(sim_time, node_features_tensor, self.gat_model)

        # 2. Append features and build 3D temporal sequence
        self.sequence_manager.append_features(node_features_tensor)
        temporal_seq = self.sequence_manager.build_temporal_sequence()

        self.gat_model.eval()
        with torch.no_grad():
            try:
                res = self.gat_model.get_strategic_vectors(
                    temporal_seq,
                    self.graph_edge_index,
                    edge_attr=self.graph_edge_attr,
                    return_prediction=True,
                )
                if isinstance(res, tuple):
                    output_vectors, future_pred = res
                    self.sequence_manager.cache_prediction(future_pred, sim_time + self.update_frequency)
                else:
                    output_vectors = res

                if len(valid_agent_indices) > 0:
                    valid_indices_tensor = torch.tensor(valid_agent_indices, device=self.device)
                    if output_vectors.shape[0] == len(node_features):
                        self.strategic_vectors.index_put_((valid_indices_tensor,), output_vectors[valid_indices_tensor])
                    else:
                        logging.error(
                            lm.get_string(
                                "strategic_coordinator.update.shape_mismatch",
                                default="Shape mismatch: output_vectors ({out}) vs node_features ({features}). Could not update strategic_vectors.",
                                out=output_vectors.shape[0],
                                features=len(node_features),
                            )
                        )
                else:
                    logging.warning(
                        lm.get_string(
                            "strategic_coordinator.update.no_valid_agents",
                            default="No agents with valid state at time {time}. strategic_vectors not updated.",
                            time=sim_time,
                        )
                    )
            except Exception as gat_err:
                logging.error(
                    lm.get_string(
                        "strategic_coordinator.update.gat_exec_error",
                        default="Error executing GAT model: {error}",
                        error=gat_err,
                    ),
                    exc_info=True,
                )

        self.last_update_time = sim_time

    def get_strategic_vector_for_agent(self, tl_id: str) -> list:
        """Returns the most recent strategic vector for a specific agent."""
        lm = self.locale_manager
        if tl_id not in self.tl_id_to_idx:
            return [0.0] * self.output_dim

        agent_idx = self.tl_id_to_idx[tl_id]
        if self.strategic_vectors is None or agent_idx >= self.strategic_vectors.shape[0]:
            logging.warning(
                lm.get_string(
                    "strategic_coordinator.vector.not_init_warning",
                    default="strategic_vectors not initialized or index {idx} out of bounds for tl_id {tl_id}.",
                    idx=agent_idx,
                    tl_id=tl_id,
                )
            )
            return [0.0] * self.output_dim

        try:
            return self.strategic_vectors[agent_idx].cpu().numpy().tolist()
        except IndexError:
            logging.error(
                lm.get_string(
                    "strategic_coordinator.vector.index_error",
                    default="IndexError accessing strategic_vectors at index {idx} for tl_id {tl_id}. Shape: {shape}",
                    idx=agent_idx,
                    tl_id=tl_id,
                    shape=self.strategic_vectors.shape,
                )
            )
            return [0.0] * self.output_dim
