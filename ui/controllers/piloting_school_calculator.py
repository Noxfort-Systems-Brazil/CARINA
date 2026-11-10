# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Topology and physical dimensioning calculator for Piloting School parameters.
Decouples SUMO network queries and maturity calculators from UI presentation.
"""

from dataclasses import dataclass
import os
from typing import Optional


@dataclass
class PilotingPacingResult:
    steps: int = 1800
    duration: float = 450.0
    min_episodes: int = 1344
    complexity: float = 1.0
    signals: int = 0
    connections: int = 0
    child_episodes: int = 1
    teen_episodes: int = 1


class PilotingSchoolCalculator:
    """Calculates episode steps, safety floor, and performance margins from SUMO network topology."""

    @staticmethod
    def calculate_pacing() -> PilotingPacingResult:
        res = PilotingPacingResult()
        try:
            from controller.map_discoverer import MapTopologyDiscoverer
            from promotion.maturity_pacing_calculator import MaturityPacingCalculator
            from utils.episode_step_calculator import EpisodeStepCalculator
            import sumolib

            map_file = MapTopologyDiscoverer.get_map_file()
            pacing_res = None
            if map_file and os.path.exists(map_file):
                try:
                    pacing_res = EpisodeStepCalculator.calculate(map_file)
                except Exception:
                    pacing_res = None

            net = None
            tls_list = []
            try:
                if map_file and os.path.exists(map_file):
                    net = sumolib.net.readNet(map_file, withInternal=False)
                    tls_list = net.getTrafficLights()
            except Exception:
                pass

            c_ep, t_ep, c_steps, _ = MaturityPacingCalculator.calculate_pacing(net, tls_list)
            res.child_episodes = c_ep
            res.teen_episodes = t_ep

            if pacing_res:
                res.steps = pacing_res.episode_steps
                res.duration = pacing_res.duration_seconds
                res.min_episodes = pacing_res.child_episodes_1_week
                res.complexity = getattr(pacing_res, "complexity_factor", getattr(pacing_res, "topological_complexity", 1.0))
                res.signals = getattr(pacing_res, "num_traffic_lights", getattr(pacing_res, "total_intersections", 0))
                res.connections = getattr(pacing_res, "num_real_streets", getattr(pacing_res, "real_connections", 0))
            else:
                res.min_episodes = c_ep
                res.steps = c_steps // max(1, c_ep)
                res.duration = res.steps * 0.25
                res.signals = len(tls_list)
        except Exception:
            pass
        return res

    @staticmethod
    def calculate_margin() -> float:
        try:
            from controller.map_discoverer import MapTopologyDiscoverer
            from promotion.performance_margin_calculator import PerformanceMarginCalculator
            import sumolib

            net = None
            try:
                map_file = MapTopologyDiscoverer.get_map_file()
                if map_file and os.path.exists(map_file):
                    net = sumolib.net.readNet(map_file, withInternal=False)
            except Exception:
                pass
            return float(PerformanceMarginCalculator.calculate_from_topology(net))
        except Exception:
            return 10.0
