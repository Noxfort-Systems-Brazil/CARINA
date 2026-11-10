# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Dedicated module for calculating dynamic episode steps and DA SILVA
maturation horizons directly from urban network graph topology.
"""

from dataclasses import dataclass
import gzip
import logging
import math
import os
from typing import Any, Dict, Optional, Set, Tuple, Union
import xml.etree.ElementTree as ET

try:
    import sumolib
except ImportError:
    sumolib = None

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EpisodePacingResult:
    """
    Encapsulates deterministic pacing metrics derived from network topology.
    """
    episode_steps: int
    duration_seconds: float
    complexity_factor: float
    num_traffic_lights: int
    num_real_streets: int
    physical_diameter_km: float
    child_episodes_1_week: int
    teen_episodes_1_week: int

    @property
    def topological_complexity(self) -> float:
        return self.complexity_factor

    @property
    def total_intersections(self) -> int:
        return self.num_traffic_lights

    @property
    def real_connections(self) -> int:
        return self.num_real_streets


class EpisodeStepCalculator:
    """
    Calculates dynamic episode step sizing based on urban network graph topology.
    Applies sub-linear graph scaling (sqrt of nodes), groups bidirectional street pairs,
    and converts physical relaxation time into base-10, multiple-of-100 step counts.
    """

    DEFAULT_TELEMETRY_DELTA_MS = 250.0
    MIN_EPISODE_STEPS = 600
    MAX_EPISODE_STEPS = 14400
    SECONDS_PER_WEEK = 604800  # 7 days * 24 hours * 3600 seconds

    @classmethod
    def calculate(
        cls,
        net_or_path: Union[str, Any],
        telemetry_delta_ms: float = DEFAULT_TELEMETRY_DELTA_MS,
    ) -> EpisodePacingResult:
        """
        Calculates episode step count and 1-week minimum episode requirements.

        Args:
            net_or_path: Path to SUMO .net.xml / .net.xml.gz file or a loaded sumolib.net.Net object.
            telemetry_delta_ms: Pessimistic frame arrival interval in milliseconds (default: 250.0 ms).

        Returns:
            EpisodePacingResult containing steps, physical duration, and maturation episode requirements.
        """
        num_tls, num_real_streets, avg_lanes, span_km = cls._extract_graph_metrics(net_or_path)

        # 1. Topological Complexity (E_real / N_tls scaled by lane capacity)
        # Clamped between 0.8 (simple linear arterial) and 1.6 (dense grid).
        base_ratio = num_real_streets / max(1, num_tls)
        lane_factor = 1.0 + 0.1 * max(0.0, avg_lanes - 1.0)
        complexity_factor = max(0.8, min(1.6, base_ratio * lane_factor))

        # 2. Sub-linear physical relaxation time:
        # T_base = 180s (3 min base observation)
        # alpha = 60s per critical corridor depth hop (sqrt of N)
        # beta = 30s per km of network geographic span
        t_physical = 180.0 + (60.0 * math.sqrt(max(1, num_tls)) + 30.0 * span_km) * complexity_factor

        # 3. Convert physical time to steps using pessimistic telemetry delta
        # delta_t = 0.25s at 250ms -> 4 steps per second.
        delta_sec = max(0.05, float(telemetry_delta_ms) / 1000.0)
        raw_steps = t_physical / delta_sec

        # 4. Enforce base-10 integer and multiple of 100 ceiling rule
        steps_multiple_100 = int(math.ceil(raw_steps / 100.0)) * 100
        clamped_steps = max(cls.MIN_EPISODE_STEPS, min(cls.MAX_EPISODE_STEPS, steps_multiple_100))

        # 5. Effective episode physical duration in seconds
        episode_duration_sec = clamped_steps * delta_sec

        # 6. Minimum episodes required to observe exactly 1 full week (7 days)
        episodes_1_week = max(1, int(math.ceil(cls.SECONDS_PER_WEEK / episode_duration_sec)))

        logger.info(
            f"[EpisodeStepCalculator] Topology parsed: TLS={num_tls}, Streets={num_real_streets}, "
            f"AvgLanes={avg_lanes:.2f}, Span={span_km:.2f}km, C_topo={complexity_factor:.2f} -> "
            f"EpisodeSteps={clamped_steps} ({episode_duration_sec:.1f}s), 1-Week Episodes={episodes_1_week}"
        )

        return EpisodePacingResult(
            episode_steps=clamped_steps,
            duration_seconds=episode_duration_sec,
            complexity_factor=complexity_factor,
            num_traffic_lights=num_tls,
            num_real_streets=num_real_streets,
            physical_diameter_km=span_km,
            child_episodes_1_week=episodes_1_week,
            teen_episodes_1_week=episodes_1_week,
        )

    @classmethod
    def _extract_graph_metrics(cls, net_or_path: Union[str, Any]) -> Tuple[int, int, float, float]:
        """
        Extracts structural features from the network:
        (num_tls, num_real_streets, avg_lanes, span_km).
        """
        if isinstance(net_or_path, str):
            return cls._parse_from_xml_file(net_or_path)
        elif net_or_path is not None and hasattr(net_or_path, "getTrafficLights"):
            return cls._parse_from_sumolib_net(net_or_path)

        # Fallback values for minimal topologies
        return 1, 4, 1.0, 1.0

    @classmethod
    def _parse_from_sumolib_net(cls, net: Any) -> Tuple[int, int, float, float]:
        """Extracts metrics from an in-memory sumolib.net.Net instance."""
        try:
            tls_list = net.getTrafficLights()
            num_tls = len(tls_list) if tls_list else 1
        except Exception:
            num_tls = 1

        # Extract real non-internal edges and group bidirectional pairs
        edge_pairs: Set[Tuple[str, str]] = set()
        total_lanes = 0

        try:
            edges = net.getEdges(withInternal=False)
        except Exception:
            edges = []

        for edge in edges:
            e_id = edge.getID()
            if not e_id or e_id.startswith(":"):
                continue

            from_id = edge.getFromNode().getID() if edge.getFromNode() else ""
            to_id = edge.getToNode().getID() if edge.getToNode() else ""
            lanes = edge.getLaneNumber() if hasattr(edge, "getLaneNumber") else 1
            total_lanes += max(1, lanes)

            # Canonical undirected street identifier to collapse bidirectional pairs
            canonical_pair = tuple(sorted([from_id, to_id])) if from_id and to_id else (e_id, "")
            edge_pairs.add(canonical_pair)

        num_real_streets = max(1, len(edge_pairs))
        num_directed_edges = max(1, len(edges))
        avg_lanes = max(1.0, float(total_lanes) / float(num_directed_edges))

        # Compute spatial span in km from bounding box
        span_km = 1.0
        try:
            bbox = net.getBBoxXY()
            dx = abs(bbox[1][0] - bbox[0][0])
            dy = abs(bbox[1][1] - bbox[0][1])
            span_km = max(0.5, math.sqrt(dx * dx + dy * dy) / 1000.0)
        except Exception:
            span_km = 1.0

        return num_tls, num_real_streets, avg_lanes, span_km

    @classmethod
    def _parse_from_xml_file(cls, path: str) -> Tuple[int, int, float, float]:
        """Parses network XML directly without mandatory sumolib dependency."""
        if not os.path.exists(path):
            logger.warning(f"[EpisodeStepCalculator] Network file not found: {path}. Using fallback values.")
            return 1, 4, 1.0, 1.0

        opener = gzip.open if path.endswith(".gz") else open
        try:
            with opener(path, "rb") as f:
                tree = ET.parse(f)
            root = tree.getroot()
        except Exception as e:
            logger.error(f"[EpisodeStepCalculator] Error parsing network XML {path}: {e}", exc_info=True)
            return 1, 4, 1.0, 1.0

        # 1. Count traffic lights
        tls_junctions = [
            j for j in root.findall("junction")
            if j.get("type") == "traffic_light" and not (j.get("id", "").startswith(":"))
        ]
        num_tls = max(1, len(tls_junctions))

        # 2. Extract edges and collapse bidirectional pairs
        edge_pairs: Set[Tuple[str, str]] = set()
        total_lanes = 0
        edge_count = 0

        for edge in root.findall("edge"):
            e_id = edge.get("id", "")
            if not e_id or e_id.startswith(":"):
                continue

            from_node = edge.get("from", "")
            to_node = edge.get("to", "")
            lanes = edge.findall("lane")
            lane_count = max(1, len(lanes))
            total_lanes += lane_count
            edge_count += 1

            canonical_pair = tuple(sorted([from_node, to_node])) if from_node and to_node else (e_id, "")
            edge_pairs.add(canonical_pair)

        num_real_streets = max(1, len(edge_pairs))
        avg_lanes = max(1.0, float(total_lanes) / float(max(1, edge_count)))

        # 3. Extract boundary coordinates from location element
        span_km = 1.0
        loc = root.find("location")
        if loc is not None:
            conv_boundary = loc.get("convBoundary")
            if conv_boundary:
                try:
                    coords = [float(x) for x in conv_boundary.split(",")]
                    dx = abs(coords[2] - coords[0])
                    dy = abs(coords[3] - coords[1])
                    span_km = max(0.5, math.sqrt(dx * dx + dy * dy) / 1000.0)
                except Exception:
                    span_km = 1.0

        return num_tls, num_real_streets, avg_lanes, span_km
