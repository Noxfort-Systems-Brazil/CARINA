# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import Any, Dict

from engine.reward_calculator import RewardCalculator


class RewardComputer:
    """
    Component specialized in calculating the immediate edge-level Reward Function
    for the HFT StepProcessor pipeline, unified with RewardCalculator's physics.
    """

    def __init__(self, settings: Any, state_extractor: Any) -> None:
        self.state_extractor = state_extractor

        self.weights = {
            "queue": settings.getfloat("REWARD_WEIGHTS", "weight_waiting_time", fallback=-2.0),
            "occupancy": settings.getfloat("REWARD_WEIGHTS", "weight_occupancy", fallback=-0.5),
            "spillback": settings.getfloat("REWARD_WEIGHTS", "weight_spillback", fallback=-25.0),
            "emergency_brake": settings.getfloat("REWARD_WEIGHTS", "weight_emergency_brake", fallback=-50.0),
            "teleport": settings.getfloat("REWARD_WEIGHTS", "weight_teleport", fallback=-300.0),
        }

        logging.info(f"[REWARD_COMPUTER] Pesos carregados: {self.weights}")

    def _resolve_edges_for_tl(self, tl_id: str) -> set[str]:
        unique_edges: set[str] = set()
        if hasattr(self.state_extractor, "tl_lanes") and tl_id in getattr(self.state_extractor, "tl_lanes", {}):
            for lane in self.state_extractor.tl_lanes[tl_id]:
                unique_edges.add(lane.rpartition("_")[0])
        elif hasattr(self.state_extractor, "tl_incoming_edges") and tl_id in getattr(
            self.state_extractor, "tl_incoming_edges", {}
        ):
            unique_edges.update(self.state_extractor.tl_incoming_edges[tl_id])
        return unique_edges

    def calculate(self, tl_id: str, edges_data: Dict[str, Any]) -> float:
        """
        Calculates the immediate multi-objective reward for a specific agent based on edge states.
        """
        reward = 0.0
        for edge in self._resolve_edges_for_tl(tl_id):
            if edge in edges_data:
                data = edges_data[edge]
                occ = float(data.get("occupancy", 0.0))
                reward += float(data.get("queue_length", 0.0)) * self.weights["queue"]
                reward += occ * self.weights["occupancy"]
                reward += RewardCalculator.compute_spillback_severity(occ) * self.weights["spillback"]
                reward += float(data.get("emergency_brakes", 0.0)) * self.weights["emergency_brake"]
                reward += float(data.get("teleports", 0.0)) * self.weights["teleport"]

        return float(reward)
