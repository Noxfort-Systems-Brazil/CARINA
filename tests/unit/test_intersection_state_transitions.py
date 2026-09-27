# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# File: tests/unit/test_intersection_state_transitions.py
# Author: Gabriel Moraes
# Date: September 2026

"""
Unit tests for IntersectionStateManager state transitions and timing behavior.
"""

import pytest

from src.controller.common_types import SignalState, StageDefinition
from src.controller.intersection_state_manager import IntersectionState, IntersectionStateManager


class MockClock:
    """Mock clock for testing time-dependent behavior."""

    def __init__(self, start_time=0.0):
        self._time = start_time

    def increment(self, seconds):
        self._time += seconds

    def time(self):
        return self._time


@pytest.fixture
def clock():
    """Provide a mock clock for time-dependent tests."""
    return MockClock()


@pytest.fixture
def state_manager():
    """Create an IntersectionStateManager with default timings."""
    return IntersectionStateManager(green_duration=15.0, yellow_duration=4.0, all_red_duration=2.0)


@pytest.fixture
def simple_intersection():
    """Create a simple intersection with two phases."""
    phases = [
        StageDefinition(state_string="GGrr", yellow_string="yyrr", all_red_string="rrrr"),
        StageDefinition(state_string="rrGG", yellow_string="rryy", all_red_string="rrrr"),
    ]
    return IntersectionState(tls_id="test_intersection", phases=phases)


class TestStateTransitions:
    """Test state transitions and timing behavior."""

    def test_starts_in_all_red(self, state_manager, simple_intersection, clock):
        """Test that intersections start in ALL_RED state."""
        state_manager.add_intersection(simple_intersection)
        state_manager.reset_all_intersections(clock.time())

        intersections = state_manager.get_all_intersections()
        intersection = intersections["test_intersection"]

        assert intersection.current_signal_state == SignalState.ALL_RED
        assert intersection.current_phase_index == 0

    def test_transition_all_red_to_green(self, state_manager, simple_intersection, clock):
        """Test transition from ALL_RED to GREEN after all-red duration."""
        state_manager.add_intersection(simple_intersection)
        state_manager.reset_all_intersections(clock.time())

        clock.increment(state_manager.all_red_duration + 0.1)
        changes = state_manager.tick(clock.time())

        assert "test_intersection" in changes
        assert changes["test_intersection"] == "GGrr"

        intersections = state_manager.get_all_intersections()
        intersection = intersections["test_intersection"]
        assert intersection.current_signal_state == SignalState.GREEN
        assert intersection.current_phase_index == 0

    def test_transition_green_to_yellow(self, state_manager, simple_intersection, clock):
        """Test transition from GREEN to YELLOW after green duration."""
        state_manager.add_intersection(simple_intersection)
        state_manager.reset_all_intersections(clock.time())

        clock.increment(state_manager.all_red_duration + 0.1)
        state_manager.tick(clock.time())

        clock.increment(state_manager.green_duration + 0.1)
        changes = state_manager.tick(clock.time())

        assert "test_intersection" in changes
        assert changes["test_intersection"] == "yyrr"

        intersections = state_manager.get_all_intersections()
        intersection = intersections["test_intersection"]
        assert intersection.current_signal_state == SignalState.YELLOW

    def test_transition_yellow_to_all_red_advances_phase(self, state_manager, simple_intersection, clock):
        """Test transition from YELLOW to ALL_RED advances to next phase."""
        state_manager.add_intersection(simple_intersection)
        state_manager.reset_all_intersections(clock.time())

        clock.increment(state_manager.all_red_duration + 0.1)
        state_manager.tick(clock.time())

        clock.increment(state_manager.green_duration + 0.1)
        state_manager.tick(clock.time())

        clock.increment(state_manager.yellow_duration + 0.1)
        changes = state_manager.tick(clock.time())

        assert "test_intersection" in changes
        assert changes["test_intersection"] == "rrrr"

        intersections = state_manager.get_all_intersections()
        intersection = intersections["test_intersection"]
        assert intersection.current_signal_state == SignalState.ALL_RED
        assert intersection.current_phase_index == 1

    def test_full_cycle_wraps_around(self, state_manager, simple_intersection, clock):
        """Test that the phase cycle wraps around correctly."""
        state_manager.add_intersection(simple_intersection)
        state_manager.reset_all_intersections(clock.time())

        clock.increment(state_manager.all_red_duration + 0.1)
        state_manager.tick(clock.time())

        clock.increment(state_manager.green_duration + 0.1)
        state_manager.tick(clock.time())

        clock.increment(state_manager.yellow_duration + 0.1)
        state_manager.tick(clock.time())

        clock.increment(state_manager.all_red_duration + 0.1)
        changes = state_manager.tick(clock.time())

        intersections = state_manager.get_all_intersections()
        intersection = intersections["test_intersection"]
        assert intersection.current_signal_state == SignalState.GREEN
        assert intersection.current_phase_index == 1

        assert len(changes) == 1
        assert changes["test_intersection"] == "rrGG"

    def test_no_changes_when_inactive(self, state_manager, simple_intersection, clock):
        """Test that no state changes occur when time hasn't advanced enough."""
        state_manager.add_intersection(simple_intersection)
        state_manager.reset_all_intersections(clock.time())

        clock.increment(state_manager.all_red_duration - 0.1)
        changes = state_manager.tick(clock.time())

        assert changes == {}
