# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import numpy as np
import sumolib

from utils.historical_aggregator import HistoricalAggregator
from utils.sumo_net_cache import read_sumo_net_cached

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend


class StateExtractor:
    """
    The "Translator" of the HFT environment.
    Converts raw Synapse data into tensors for the AI,
    using the static topology extracted from the .net.xml map.
    """

    def __init__(self, locale_manager: "LocaleManagerBackend") -> None:
        self.locale_manager = locale_manager
        self.lm = locale_manager

        self.tl_incoming_edges: Dict[str, List[str]] = {}
        self.tl_green_stages: Dict[str, List[int]] = {}

        # Maps ID_SEMAFORO -> { ID_FASE: STRING_ESTADO }
        self.tl_stage_codes: Dict[str, Dict[int, str]] = {}

        # Maps ID_SEMAFORO -> { ID_FASE: DURATION }
        self.tl_stage_durations: Dict[str, Dict[int, float]] = {}

        # NEW: Maps ID_SEMAFORO -> List of Lane Lists by Index
        # Ex: 'C1' -> [ ['edge1_0', 'edge1_1'], ['edge2_0'] ]
        # Where the index of the external list matches the character in the state string.
        self.tl_controlled_lanes_map: Dict[str, List[List[str]]] = {}

        # Physical vehicle capacities per incoming edge (length * lanes / 7.0m)
        self.tl_edge_capacities: Dict[str, List[float]] = {}

        # Historical aggregators for 5-minute context
        self.aggregators: Dict[str, HistoricalAggregator] = {}

        self.topology_loaded = False

        logging.info(
            self.lm.get_string("state_extractor.init.sensor_created", fallback="StateExtractor (HFT) inicializado.")
        )

    def load_topology(self, net_file_path: str) -> None:
        """
        Reads the .net.xml file and maps connections.
        """
        logging.info(f"Carregando topologia do mapa: {net_file_path}")
        try:
            net = read_sumo_net_cached(
                net_file_path, reader_fn=sumolib.net.readNet, with_programs=True, with_internal=False
            )

            self.tl_incoming_edges.clear()
            self.tl_green_stages.clear()
            self.tl_stage_codes.clear()
            self.tl_stage_durations.clear()
            self.tl_controlled_lanes_map.clear()
            self.tl_edge_capacities.clear()
            self.aggregators.clear()

            for tls in net.getTrafficLights():
                tl_id = tls.getID()
                incoming_edges = set()
                edge_cap_by_id: Dict[str, float] = {}
                controlled_lanes_by_index = []

                try:
                    # tls.getConnections() returns a list of connection lists.
                    # The order of this external list exactly matches the indices of the state string (ryg).
                    connections_list = tls.getConnections()

                    for link_index, link_connections in enumerate(connections_list):
                        lanes_for_this_index = []

                        for item in link_connections:
                            lane_obj = None
                            # Robust Lane/Edge Extraction
                            if hasattr(item, "getFromLane"):  # modern sumolib
                                lane_obj = item.getFromLane()
                            elif hasattr(item, "getEdge"):  # old sumolib or direct Lane object
                                lane_obj = item

                            if lane_obj:
                                # Save Lane ID for Map View UI
                                lanes_for_this_index.append(lane_obj.getID())

                                # Guard Edge ID and physical capacity for AI State Vector
                                if hasattr(lane_obj, "getEdge"):
                                    edge = lane_obj.getEdge()
                                    if edge:
                                        eid = edge.getID()
                                        incoming_edges.add(eid)
                                        if eid not in edge_cap_by_id:
                                            edge_cap_by_id[eid] = self._estimate_edge_capacity(edge)

                        controlled_lanes_by_index.append(lanes_for_this_index)

                except Exception as e_conn:
                    logging.warning(f"Erro ao extrair conexões para TLS {tl_id}: {e_conn}", exc_info=True)

                self.tl_incoming_edges[tl_id] = sorted(list(incoming_edges))
                self.tl_edge_capacities[tl_id] = [
                    edge_cap_by_id.get(eid, 20.0) for eid in self.tl_incoming_edges[tl_id]
                ]
                self.tl_controlled_lanes_map[tl_id] = controlled_lanes_by_index

                # Program Extraction (Phases and Colors)
                programs = tls.getPrograms()
                self.tl_stage_codes[tl_id] = {}
                self.tl_stage_durations[tl_id] = {}

                if programs:
                    logic = next(iter(programs.values()))
                    green_stages = []
                    for i, stage in enumerate(logic.getPhases()):
                        state = stage.state
                        self.tl_stage_codes[tl_id][i] = state
                        self.tl_stage_durations[tl_id][i] = float(stage.duration)
                        state_upper = state.upper()
                        # A stage is green if it has green phases and no yellow phases
                        if ("G" in state_upper) and ("Y" not in state_upper):
                            green_stages.append(i)

                    self.tl_green_stages[tl_id] = green_stages
                    logging.info(
                        f"[StateExtractor] TL {tl_id} loaded from network file: {len(self.tl_stage_codes[tl_id])} stages detected. Green stages: {green_stages}"
                    )
                else:
                    self.tl_green_stages[tl_id] = [0, 3]
                    self.tl_stage_codes[tl_id] = {0: "G", 1: "y", 2: "r", 3: "G", 4: "y", 5: "r"}
                    # Fallback durations: stage 2 is clearance (3s), stage 5 is normal red (10s)
                    self.tl_stage_durations[tl_id] = {0: 30.0, 1: 4.0, 2: 3.0, 3: 30.0, 4: 4.0, 5: 10.0}

            self.topology_loaded = True
            logging.info(f"Topologia carregada. {len(self.tl_incoming_edges)} semáforos mapeados.")

        except Exception as e:
            logging.error(f"Erro fatal ao ler topologia com sumolib: {e}", exc_info=True)
            self.topology_loaded = False

    def _build_raw_state(
        self, traffic_frame: Dict[str, Any], tl_id: str, current_stage_idx: int
    ) -> Optional[np.ndarray]:
        """Builds the raw un-aggregated feature vector for `tl_id`, or `None` if unavailable."""
        if not self.topology_loaded:
            return None

        incoming_edges = self.tl_incoming_edges.get(tl_id, [])
        if not incoming_edges:
            return None

        edges_data = traffic_frame.get("edges", {})
        default_edge = {"occupancy": 0.0, "mean_speed": 0.0, "queue_length": 0}

        sensor_data = [
            val
            for edge_id in incoming_edges
            for state in (edges_data.get(edge_id, default_edge),)
            for val in (
                state["occupancy"],
                min(state["mean_speed"] / 13.89, 1.0),
                min(state["queue_length"] / 20.0, 1.0),
            )
        ]

        valid_green_phases = self.tl_green_stages.get(tl_id, [])
        num_green_phases = max(len(valid_green_phases), 1)

        phase_one_hot = [0.0] * num_green_phases
        if current_stage_idx in valid_green_phases:
            try:
                phase_one_hot[valid_green_phases.index(current_stage_idx)] = 1.0
            except ValueError:
                pass

        ped_calls = 0.0
        if "tls_telemetry" in traffic_frame:
            telemetry = traffic_frame["tls_telemetry"].get(tl_id, {})
            ped_calls = 1.0 if telemetry.get("active_ped_calls", 0) > 0 else 0.0

        return np.array(sensor_data + phase_one_hot + [ped_calls], dtype=np.float32)

    def extract_state(self, traffic_frame: Dict[str, Any], tl_id: str, current_stage_idx: int) -> np.ndarray:
        """
        Extracts the state using HFT-vectorized comprehension arrays, updating historical statistics once per step.
        """
        raw_state = self._build_raw_state(traffic_frame, tl_id, current_stage_idx)
        if raw_state is None:
            return np.array([], dtype=np.float32)

        # Apply 5-minute historical aggregation
        if tl_id not in self.aggregators:
            self.aggregators[tl_id] = HistoricalAggregator(len(raw_state))

        return self.aggregators[tl_id].update(raw_state)

    def peek_state(self, traffic_frame: Dict[str, Any], tl_id: str, current_stage_idx: int) -> np.ndarray:
        """
        Computes the aggregated state vector without mutating running HistoricalAggregator EMAs/peaks.
        Used by secondary consumers (e.g., StrategicCoordinator) reading the same simulation step.
        """
        raw_state = self._build_raw_state(traffic_frame, tl_id, current_stage_idx)
        if raw_state is None:
            return np.array([], dtype=np.float32)

        aggregator = self.aggregators.get(tl_id)
        if aggregator is None:
            return HistoricalAggregator(len(raw_state)).peek(raw_state)
        return aggregator.peek(raw_state)

    @staticmethod
    def _estimate_edge_capacity(edge: Any) -> float:
        """Estimates vehicle holding capacity `(length * lanes) / 7.0m` from sumolib edge."""
        raw_len = edge.getLength() if hasattr(edge, "getLength") else None
        raw_lanes = edge.getLaneNumber() if hasattr(edge, "getLaneNumber") else None
        length = float(raw_len) if isinstance(raw_len, (int, float)) and not isinstance(raw_len, bool) else 140.0
        lanes = int(raw_lanes) if isinstance(raw_lanes, (int, float)) and not isinstance(raw_lanes, bool) else 1
        return max(1.0, (length * max(1, lanes)) / 7.0)

    def get_edge_feature_dim(self, tl_id: str) -> int:
        """Returns the number of raw edge telemetry features (3 per incoming edge)."""
        return len(self.tl_incoming_edges.get(tl_id, [])) * 3

    def get_edge_capacities(self, tl_id: str) -> List[float]:
        """Returns estimated vehicle capacities per incoming edge for saturation normalization."""
        return list(self.tl_edge_capacities.get(tl_id, []))

    def get_observation_space_size(self, tl_id: str) -> int:
        if not self.topology_loaded:
            return 0
        num_edges = len(self.tl_incoming_edges.get(tl_id, []))
        num_phases = len(self.tl_green_stages.get(tl_id, []))
        if num_phases == 0:
            num_phases = 1
        raw_size = (num_edges * 3) + num_phases + 1  # +1 for pedestrian calls
        return raw_size * 5

    def get_phase_lane_states(self, tl_id: str, phase_index: int) -> Dict[str, str]:
        """
        Returns a dictionary { lane_id: 'G'|'r'|'y' } for the UI.
        Converts the raw state string using the topology map.
        """
        if not self.topology_loaded:
            return {}

        state_string = self.tl_stage_codes.get(tl_id, {}).get(phase_index, "")
        lanes_map = self.tl_controlled_lanes_map.get(tl_id, [])

        result = {}

        # Iterates over the string (ex: "GrGr")
        # The character at index 'i' applies to all lanes in lanes_map[i]
        for i, char_state in enumerate(state_string):
            if i < len(lanes_map):
                target_lanes = lanes_map[i]
                for lane_id in target_lanes:
                    result[lane_id] = char_state

        return result
