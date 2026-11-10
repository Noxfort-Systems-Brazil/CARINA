# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Unit tests for EpisodeStepCalculator.
Verifies base-10 multiple-of-100 step constraints, bidirectional street pairing,
sub-linear graph scaling, and 1-week DA SILVA maturation episode pacing.
"""

import types
import pytest
from src.utils.episode_step_calculator import EpisodeStepCalculator, EpisodePacingResult


class MockNode:
    def __init__(self, node_id: str):
        self._id = node_id

    def getID(self) -> str:
        return self._id


class MockEdge:
    def __init__(self, edge_id: str, from_id: str, to_id: str, lanes: int = 1):
        self._id = edge_id
        self._from = MockNode(from_id)
        self._to = MockNode(to_id)
        self._lanes = lanes

    def getID(self) -> str:
        return self._id

    def getFromNode(self):
        return self._from

    def getToNode(self):
        return self._to

    def getLaneNumber(self) -> int:
        return self._lanes


class MockNet:
    def __init__(self, num_tls: int, edges, bbox=((0.0, 0.0), (1000.0, 1000.0))):
        self._tls = [f"tls_{i}" for i in range(num_tls)]
        self._edges = edges
        self._bbox = bbox

    def getTrafficLights(self):
        return self._tls

    def getEdges(self, withInternal: bool = False):
        return self._edges

    def getBBoxXY(self):
        return self._bbox


def test_step_count_is_base_10_multiple_of_100():
    """Verifies that computed episode steps are strictly integers and multiples of 100."""
    net = MockNet(num_tls=4, edges=[
        MockEdge("e1", "n1", "n2", 2),
        MockEdge("-e1", "n2", "n1", 2),
    ])

    result = EpisodeStepCalculator.calculate(net, telemetry_delta_ms=250.0)

    assert isinstance(result.episode_steps, int)
    assert result.episode_steps % 100 == 0
    assert result.episode_steps >= EpisodeStepCalculator.MIN_EPISODE_STEPS
    assert result.episode_steps <= EpisodeStepCalculator.MAX_EPISODE_STEPS


def test_bidirectional_pairing_collapses_opposing_edges():
    """Ensures two-way streets (forward and reverse edges) are counted as one physical street."""
    edges = [
        MockEdge("main_fwd", "node_a", "node_b", 2),
        MockEdge("main_rev", "node_b", "node_a", 2),
        MockEdge("cross_fwd", "node_c", "node_d", 1),
        MockEdge("cross_rev", "node_d", "node_c", 1),
        MockEdge(":internal_0", "node_a", "node_a", 1),  # Internal edge, should be filtered
    ]
    net = MockNet(num_tls=2, edges=edges)

    result = EpisodeStepCalculator.calculate(net, telemetry_delta_ms=250.0)

    # 4 directed edges forming 2 real streets
    assert result.num_real_streets == 2
    assert result.num_traffic_lights == 2


def test_sublinear_scaling_across_network_scales():
    """Validates that episode steps scale sub-linearly with traffic light count sqrt(N)."""
    # Small neighborhood: 4 TLS, 1 km
    small_net = MockNet(num_tls=4, edges=[], bbox=((0.0, 0.0), (1000.0, 1000.0)))
    small_res = EpisodeStepCalculator.calculate(small_net)

    # Medium city: 100 TLS, 6 km
    med_net = MockNet(num_tls=100, edges=[], bbox=((0.0, 0.0), (4242.0, 4242.0)))
    med_res = EpisodeStepCalculator.calculate(med_net)

    # Metropolis: 1000 TLS, 22 km
    big_net = MockNet(num_tls=1000, edges=[], bbox=((0.0, 0.0), (15556.0, 15556.0)))
    big_res = EpisodeStepCalculator.calculate(big_net)

    # Steps must increase with scale, but stay within traffic engineering boundaries
    assert small_res.episode_steps < med_res.episode_steps < big_res.episode_steps
    assert small_res.episode_steps >= 600
    assert big_res.episode_steps <= 14400

    # 1-week episode counts must correspondingly decrease as episode duration increases
    assert small_res.child_episodes_1_week > med_res.child_episodes_1_week > big_res.child_episodes_1_week


def test_telemetry_jitter_effect():
    """Tests that varying frame arrival intervals (150ms vs 250ms) preserves multiple-of-100 constraint."""
    net = MockNet(num_tls=16, edges=[])

    res_150 = EpisodeStepCalculator.calculate(net, telemetry_delta_ms=150.0)
    res_250 = EpisodeStepCalculator.calculate(net, telemetry_delta_ms=250.0)

    assert res_150.episode_steps % 100 == 0
    assert res_250.episode_steps % 100 == 0
    # Faster telemetry means more steps are captured within the same physical duration
    assert res_150.episode_steps >= res_250.episode_steps
