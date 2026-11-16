# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""P0 safety sanitization and street-block filtering for incoming Synapse traffic frames."""

import logging
import math
from typing import Any, Dict

logger = logging.getLogger(__name__)


class FrameSanitizer:
    """Validates, clamps, and sanitizes telemetry metrics, timestamps, sequence IDs, and blocked edges."""

    OCCUPANCY_MIN: float = 0.0
    OCCUPANCY_MAX: float = 1.0

    SPEED_MIN: float = 0.0
    SPEED_MAX: float = 100.0  # m/s (~360 km/h)

    QUEUE_MIN: float = 0.0
    QUEUE_MAX: float = 1000.0  # vehicle units / meters

    DENSITY_MIN: float = 0.0
    DENSITY_MAX: float = 1.0

    @classmethod
    def sanitize_metric(
        cls,
        val: Any,
        min_val: float,
        max_val: float,
        default: float = 0.0,
        field_name: str = "",
        edge_id: str = "",
    ) -> float:
        """Validates numeric input with `math.isnan`/`math.isinf` and clamps to `[min_val, max_val]`."""
        try:
            f_val = float(val) if val is not None else default
        except (ValueError, TypeError):
            logger.warning(
                "[TrafficFrameProcessor] Invalid numeric type for %s on edge %s: %s. Sanitizing to %.2f.",
                field_name,
                edge_id,
                val,
                default,
            )
            return default

        if math.isnan(f_val) or math.isinf(f_val):
            logger.warning(
                "[TrafficFrameProcessor] Numerical anomaly (NaN/Inf) detected for %s on edge %s: %s. Sanitizing to %.2f.",
                field_name,
                edge_id,
                f_val,
                default,
            )
            return default

        return max(min_val, min(max_val, f_val))

    @staticmethod
    def sanitize_timestamp(raw_ts: Any) -> float:
        try:
            current_time = float(raw_ts)
            if math.isnan(current_time) or math.isinf(current_time) or current_time < 0.0:
                logger.warning(
                    "[TrafficFrameProcessor] Anomaly detected: invalid timestamp %s. Sanitizing to 0.0.",
                    raw_ts,
                )
                return 0.0
            return current_time
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def sanitize_sequence_id(raw_seq: Any) -> int:
        try:
            return max(0, int(raw_seq))
        except (ValueError, TypeError):
            return 0

    @classmethod
    def sanitize_edge_state(cls, edge_id: str, state: Any) -> Dict[str, float]:
        """Extracts, validates, and clamps all metrics for a single edge state."""
        is_dict = isinstance(state, dict)
        raw_occ = state.get("occupancy") if is_dict else getattr(state, "occupancy", None)
        raw_speed = state.get("mean_speed") if is_dict else getattr(state, "mean_speed", None)
        raw_queue = state.get("queue_length") if is_dict else getattr(state, "queue_length", None)

        edge_data = {
            "occupancy": cls.sanitize_metric(
                raw_occ, cls.OCCUPANCY_MIN, cls.OCCUPANCY_MAX, default=0.0, field_name="occupancy", edge_id=edge_id
            ),
            "mean_speed": cls.sanitize_metric(
                raw_speed, cls.SPEED_MIN, cls.SPEED_MAX, default=0.0, field_name="mean_speed", edge_id=edge_id
            ),
            "queue_length": cls.sanitize_metric(
                raw_queue, cls.QUEUE_MIN, cls.QUEUE_MAX, default=0.0, field_name="queue_length", edge_id=edge_id
            ),
        }

        raw_density = state.get("density") if is_dict else getattr(state, "density", None)
        if raw_density is not None:
            edge_data["density"] = cls.sanitize_metric(
                raw_density, cls.DENSITY_MIN, cls.DENSITY_MAX, default=0.0, field_name="density", edge_id=edge_id
            )
        return edge_data

    @staticmethod
    def is_edge_blocked(edge_id: str, override_manager: Any) -> bool:
        if not override_manager or not override_manager.active_street_overrides:
            return False
        overrides = override_manager.active_street_overrides
        if overrides.get(edge_id) == "BLOCKED":
            return True
        base_sibling = edge_id[1:] if edge_id.startswith("-") else edge_id
        reverse_sibling = "-" + base_sibling if not edge_id.startswith("-") else base_sibling
        return overrides.get(base_sibling) == "BLOCKED" or overrides.get(reverse_sibling) == "BLOCKED"

    @classmethod
    def build_clean_edges(cls, frame: Any, override_manager: Any) -> Dict[str, Dict[str, float]]:
        frame_edges = getattr(frame, "edges", {}) or {}
        edge_items = frame_edges.items() if hasattr(frame_edges, "items") else []
        cleaned: Dict[str, Dict[str, float]] = {}
        for edge_id, state in edge_items:
            if cls.is_edge_blocked(edge_id, override_manager):
                blocked_data = {"occupancy": 0.0, "mean_speed": 0.0, "queue_length": 0.0}
                if hasattr(state, "density") or (isinstance(state, dict) and "density" in state):
                    blocked_data["density"] = 0.0
                cleaned[edge_id] = blocked_data
            else:
                cleaned[edge_id] = cls.sanitize_edge_state(edge_id, state)
        return cleaned
