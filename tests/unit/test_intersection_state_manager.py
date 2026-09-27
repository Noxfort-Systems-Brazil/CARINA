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

# File: tests/unit/test_intersection_state_manager.py
# Author: Gabriel Moraes
# Date: April 25, 2026

"""
Unit tests for the IntersectionStateManager component.
"""

import time
from unittest.mock import MagicMock, patch

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


class TestIntersectionStateManagerInitialization:
    """Test initialization of IntersectionStateManager."""

    def test_valid_initialization(self):
        """Test that the manager initializes with valid timing parameters."""
        manager = IntersectionStateManager(green_duration=20.0, yellow_duration=5.0, all_red_duration=3.0)

        assert manager.green_duration == 20.0
        assert manager.yellow_duration == 5.0
        assert manager.all_red_duration == 3.0
        assert len(manager.get_all_intersections()) == 0

    def test_zero_timing_raises_error(self):
        """Test that zero timing values raise ValueError."""
        with pytest.raises(ValueError):
            IntersectionStateManager(green_duration=0.0, yellow_duration=4.0, all_red_duration=2.0)

        with pytest.raises(ValueError):
            IntersectionStateManager(green_duration=15.0, yellow_duration=0.0, all_red_duration=2.0)

        with pytest.raises(ValueError):
            IntersectionStateManager(green_duration=15.0, yellow_duration=4.0, all_red_duration=0.0)


class TestIntersectionManagement:
    """Test adding, removing, and retrieving intersections."""

    def test_add_intersection(self, state_manager, simple_intersection):
        """Test adding an intersection to the manager."""
        state_manager.add_intersection(simple_intersection)

        retrieved = state_manager.get_intersection("test_intersection")
        assert retrieved is not None
        assert retrieved.tls_id == "test_intersection"
        assert len(retrieved.phases) == 2

        all_intersections = state_manager.get_all_intersections()
        assert "test_intersection" in all_intersections
        assert all_intersections["test_intersection"] is simple_intersection

    def test_remove_intersection(self, state_manager, simple_intersection):
        """Test removing an intersection from the manager."""
        state_manager.add_intersection(simple_intersection)
        assert state_manager.get_intersection("test_intersection") is not None

        state_manager.remove_intersection("test_intersection")
        assert state_manager.get_intersection("test_intersection") is None

        all_intersections = state_manager.get_all_intersections()
        assert "test_intersection" not in all_intersections

    def test_get_nonexistent_intersection(self, state_manager):
        """Test retrieving a non-existent intersection returns None."""
        assert state_manager.get_intersection("nonexistent") is None


class TestSafetyFeatures:
    """Test safety features of the IntersectionStateManager."""

    def test_final_safety_check_rejects_invalid_characters(self, state_manager):
        """Test that invalid characters in state strings are rejected."""
        invalid_phase = StageDefinition(state_string="GGxrr", yellow_string="yyxrr", all_red_string="rrxrr")

        invalid_intersection = IntersectionState(tls_id="invalid_intersection", phases=[invalid_phase])

        state_manager.add_intersection(invalid_intersection)
        state_manager.reset_all_intersections(0.0)

        changes = state_manager.tick(state_manager.all_red_duration + 0.1)

        assert "invalid_intersection" in changes
        assert changes["invalid_intersection"] == "rrrrr"


class TestResetAndAllRed:
    """Test reset and all-red functionality."""

    def test_reset_all_intersections(self, state_manager, simple_intersection, clock):
        """Test resetting all intersections to initial state."""
        state_manager.add_intersection(simple_intersection)
        state_manager.reset_all_intersections(clock.time())

        clock.increment(state_manager.all_red_duration + 0.1)
        state_manager.tick(clock.time())

        intersections = state_manager.get_all_intersections()
        intersection = intersections["test_intersection"]
        assert intersection.current_signal_state == SignalState.GREEN

        clock.increment(1.0)
        state_manager.reset_all_intersections(clock.time())

        intersections = state_manager.get_all_intersections()
        intersection = intersections["test_intersection"]
        assert intersection.current_signal_state == SignalState.ALL_RED
        assert intersection.current_phase_index == 0
        assert intersection.state_start_time == clock.time()

    def test_set_all_red(self, state_manager, simple_intersection, clock):
        """Test setting all intersections to ALL_RED state."""
        state_manager.add_intersection(simple_intersection)
        state_manager.reset_all_intersections(clock.time())

        clock.increment(state_manager.all_red_duration + 0.1)
        state_manager.tick(clock.time())

        intersections = state_manager.get_all_intersections()
        intersection = intersections["test_intersection"]
        assert intersection.current_signal_state == SignalState.GREEN

        state_manager.set_all_red()

        intersections = state_manager.get_all_intersections()
        intersection = intersections["test_intersection"]
        assert intersection.current_signal_state == SignalState.ALL_RED
