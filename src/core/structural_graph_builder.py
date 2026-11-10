# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import Any, Dict, List, Tuple

import torch

from core.system_reporter import SystemReporter
from utils.network_parser import build_structural_neighborhood_map


class StructuralGraphBuilder:
    """Extracts network topology from simulation, constructs edge indices, and evaluates observation dimensions."""

    @staticmethod
    def build_network_graph(
        traci_conn: Any,
        device: Any,
        lm: Any,
    ) -> Tuple[torch.Tensor, int, Dict[str, int], Dict[int, str], int, int, torch.Tensor]:
        """
        Builds the network graph edge_index, edge_attr, and calculates maximum observation state dimensions.
        Returns:
            (graph_edge_index, max_state_dim, tl_id_to_idx, tl_idx_to_id, num_nodes, num_edges, graph_edge_attr)
        """
        net_file = traci_conn.simulation.getOption("net-file")
        tls_ids = sorted(traci_conn.trafficlight.getIDList())
        if not tls_ids:
            raise ValueError("No traffic lights found in the simulation to initialize the Strategic Coordinator.")

        num_nodes = len(tls_ids)
        tl_id_to_idx = {tl_id: i for i, tl_id in enumerate(tls_ids)}
        tl_idx_to_id = {i: tl_id for i, tl_id in enumerate(tls_ids)}

        neighborhoods = build_structural_neighborhood_map(net_file_path=net_file, tls_ids_in_sim=tls_ids, lm=lm)

        edge_list = []
        edge_attr_list = []
        for tl_id, neighbors in neighborhoods.items():
            for neighbor_id in neighbors:
                if tl_id in tl_id_to_idx and neighbor_id in tl_id_to_idx:
                    edge_list.append([tl_id_to_idx[tl_id], tl_id_to_idx[neighbor_id]])
                    dist = 200.0
                    spd = 13.89  # Default ~50 km/h
                    try:
                        if hasattr(traci_conn, "junction") and hasattr(traci_conn.junction, "getPosition"):
                            p1 = traci_conn.junction.getPosition(tl_id)
                            p2 = traci_conn.junction.getPosition(neighbor_id)
                            dx = float(p1[0]) - float(p2[0])
                            dy = float(p1[1]) - float(p2[1])
                            dist = max(20.0, (dx * dx + dy * dy) ** 0.5)
                    except Exception:
                        dist = 200.0
                    tt = dist / spd
                    # Normalized: distance in km, speed relative to 30 m/s (~108 km/h), travel time in minutes
                    edge_attr_list.append([dist / 1000.0, spd / 30.0, tt / 60.0])

        if edge_list:
            graph_edge_index = torch.tensor(edge_list, dtype=torch.long).t().contiguous().to(device)
            graph_edge_attr = torch.tensor(edge_attr_list, dtype=torch.float32).to(device)
        else:
            graph_edge_index = torch.empty((2, 0), dtype=torch.long, device=device)
            graph_edge_attr = torch.empty((0, 3), dtype=torch.float32, device=device)

        logging.info(
            lm.get_string(
                "strategic_coordinator.initialize.edge_index_created",
                default="[StrategicCoordinator] graph_edge_index created on {device} with shape: {shape}",
                device=device,
                shape=graph_edge_index.shape,
            )
        )

        num_edges = graph_edge_index.size(1) if graph_edge_index.dim() == 2 else 0
        SystemReporter.report_graph_structure(num_nodes=num_nodes, num_edges=num_edges, lm=lm)

        all_state_dims = []
        for tl_id in tls_ids:
            try:
                num_lanes = len(set(traci_conn.trafficlight.getControlledLanes(tl_id)))
                logic_defs = traci_conn.trafficlight.getCompleteRedYellowGreenDefinition(tl_id)
                if not logic_defs:
                    logging.warning(
                        lm.get_string(
                            "strategic_coordinator.initialize.no_logic_found",
                            default="No logic definition found for TL {tl_id}, using 0 green phases.",
                            tl_id=tl_id,
                        )
                    )
                    num_green_phases = 0
                else:
                    logic = logic_defs[0]
                    num_green_phases = len(
                        [p for p in logic.phases if "g" in p.state.lower() and "y" not in p.state.lower()]
                    )
                all_state_dims.append(num_lanes + num_green_phases)
            except Exception as e:
                logging.warning(
                    lm.get_string(
                        "strategic_coordinator.initialize.dim_error",
                        default="Error obtaining dimensions for TL {tl_id}: {error}",
                        tl_id=tl_id,
                        error=e,
                    )
                , exc_info=True)

        max_state_dim = max(all_state_dims) if all_state_dims else 0
        logging.info(lm.get_string("strategic_coordinator.initialize.max_state_dim", size=max_state_dim))

        if max_state_dim <= 0:
            logging.error(
                lm.get_string(
                    "strategic_coordinator.initialize.zero_dim_error",
                    default="max_state_dim calculated as zero or negative. Cannot initialize GAT model.",
                )
            )
            raise ValueError("Calculated max_state_dim is zero or negative.")

        return graph_edge_index, max_state_dim, tl_id_to_idx, tl_idx_to_id, num_nodes, num_edges

    @staticmethod
    def extract_padded_features(
        current_states_dict: Dict[str, Any],
        tl_idx_to_id: Dict[int, str],
        num_agents: int,
        max_state_dim: int,
        sim_time: float,
        lm: Any,
    ) -> Tuple[List[List[float]], List[int]]:
        """Prepares padded node features and tracks valid agent indices for GAT model input."""
        node_features = []
        valid_agent_indices = []

        for i in range(num_agents):
            tl_id = tl_idx_to_id.get(i)
            if not tl_id:
                continue

            state = current_states_dict.get(tl_id)
            if state is None or not isinstance(state, list):
                logging.debug(
                    lm.get_string(
                        "strategic_coordinator.update.invalid_state_debug",
                        default="Invalid or missing state for {tl_id} at time {time}. Using padding.",
                        tl_id=tl_id,
                        time=sim_time,
                    )
                )
                padded_state = [0.0] * max_state_dim
            else:
                current_len = len(state)
                padding_needed = max(0, max_state_dim - current_len)
                padded_state = state + ([0.0] * padding_needed)
                padded_state = padded_state[:max_state_dim]
                valid_agent_indices.append(i)

            node_features.append(padded_state)

        return node_features, valid_agent_indices
