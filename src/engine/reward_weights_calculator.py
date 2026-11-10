# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Reward Weights Calculator for Reinforcement Learning Balancing.

Calculates dynamically balanced reward weights (waiting time penalty vs vehicle flow bonus)
based on urban network topology physics (characteristic link travel time and saturation flow).
"""

import logging
from typing import Any, Tuple

logger = logging.getLogger(__name__)


class RewardWeightsCalculator:
    """
    Calculates dynamically balanced reward weights (waiting time penalty vs vehicle flow bonus)
    based on urban network topology physics (characteristic link travel time).
    """

    DEFAULT_WAITING_WEIGHT: float = -1.0
    DEFAULT_FLOW_WEIGHT: float = 10.0
    MIN_FLOW_WEIGHT: float = 2.0
    MAX_FLOW_WEIGHT: float = 25.0

    @classmethod
    def calculate_weights(
        cls,
        mean_length: float,
        mean_speed_limit: float,
        alpha: float = 1.0,
        min_flow: float = 2.0,
        max_flow: float = 25.0,
    ) -> Tuple[float, float]:
        """
        Calculates balanced reward weights (waiting_time, flow) based on characteristic link travel time:
        tau = mean_length / mean_speed_limit (seconds)
        w_wait = -1.0
        w_flow = clamp(min_flow, max_flow, round(tau * alpha, 2))

        Args:
            mean_length: Average length of controlled road links (meters).
            mean_speed_limit: Average speed limit of controlled road links (m/s).
            alpha: Tuning multiplier for flow encouragement (default 1.0).
            min_flow: Lower clamp bound for flow weight.
            max_flow: Upper clamp bound for flow weight.

        Returns:
            Tuple of (weight_waiting_time, weight_flow).
        """
        if mean_speed_limit <= 0.1 or mean_length <= 0.1:
            return (cls.DEFAULT_WAITING_WEIGHT, cls.DEFAULT_FLOW_WEIGHT)

        tau = float(mean_length) / float(mean_speed_limit)
        raw_flow = tau * float(alpha)
        clamped_flow = max(float(min_flow), min(float(max_flow), round(raw_flow, 2)))

        return (cls.DEFAULT_WAITING_WEIGHT, clamped_flow)

    @classmethod
    def calculate_from_topology(cls, net: Any, settings: Any = None) -> Tuple[float, float]:
        """
        Extracts link geometry (lengths and speed limits) from SUMO network topology
        and computes the balanced reward weights.
        """
        if not net or not hasattr(net, "getEdges"):
            return (cls.DEFAULT_WAITING_WEIGHT, cls.DEFAULT_FLOW_WEIGHT)

        edges = net.getEdges()
        if not edges:
            return (cls.DEFAULT_WAITING_WEIGHT, cls.DEFAULT_FLOW_WEIGHT)

        valid_edges = [
            e for e in edges
            if hasattr(e, "getSpeed") and e.getSpeed() > 0.1
            and hasattr(e, "getLength") and e.getLength() > 0.1
        ]

        if not valid_edges:
            return (cls.DEFAULT_WAITING_WEIGHT, cls.DEFAULT_FLOW_WEIGHT)

        avg_length = sum(e.getLength() for e in valid_edges) / len(valid_edges)
        avg_speed = sum(e.getSpeed() for e in valid_edges) / len(valid_edges)

        return cls.calculate_weights(mean_length=avg_length, mean_speed_limit=avg_speed)

    @classmethod
    def apply_if_enabled(
        cls,
        target: Any,
        weights: Tuple[float, float],
        settings: Any,
    ) -> bool:
        """
        If automatic reward weight balancing is enabled in settings,
        injects the calculated weights into the target (RewardCalculator)
        and/or updates settings in-memory.

        Returns:
            True if applied, False otherwise.
        """
        is_enabled = True
        if settings is not None:
            if hasattr(settings, "getboolean"):
                try:
                    is_enabled = settings.getboolean("REWARD_WEIGHTS", "auto_reward_weights_enabled", fallback=True)
                except Exception:
                    is_enabled = True
            elif isinstance(settings, dict):
                val = str(settings.get("auto_reward_weights_enabled", "True")).lower()
                is_enabled = val in ("true", "1", "yes")

        if not is_enabled:
            return False

        w_wait, w_flow = weights

        # 1. Update settings in memory if available
        if settings is not None:
            if hasattr(settings, "set") and hasattr(settings, "has_section"):
                if not settings.has_section("REWARD_WEIGHTS"):
                    settings.add_section("REWARD_WEIGHTS")
                settings.set("REWARD_WEIGHTS", "weight_waiting_time", str(w_wait))
                settings.set("REWARD_WEIGHTS", "weight_flow", str(w_flow))
            elif isinstance(settings, dict):
                settings["weight_waiting_time"] = str(w_wait)
                settings["weight_flow"] = str(w_flow)

        # 2. Update target if callable
        if target is not None and hasattr(target, "set_reward_weights"):
            target.set_reward_weights(w_wait, w_flow)

        logger.info(
            f"[RewardWeightsCalculator] Auto reward weights applied: waiting_time={w_wait:.2f}, flow={w_flow:.2f}"
        )
        return True
