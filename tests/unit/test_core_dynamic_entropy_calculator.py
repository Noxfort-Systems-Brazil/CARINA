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

# File: tests/unit/test_core_dynamic_entropy_calculator.py
# Author: Gabriel Moraes
# Date: September 2026

import math

import pytest

from core.dynamic_entropy_calculator import DynamicEntropyCalculator


def test_dynamic_entropy_zero_or_negative_episodes():
    """Zero or negative configured episodes must return the maximum ceiling (e_max)."""
    calc = DynamicEntropyCalculator(e_max=1.8, e_ideal=0.1)
    assert calc.calculate_threshold(0) == 1.8
    assert calc.calculate_threshold(-5) == 1.8


def test_dynamic_entropy_decay_curve():
    """Threshold should decay toward e_ideal as configured episodes increase."""
    calc = DynamicEntropyCalculator(e_max=1.8, e_ideal=0.1)

    t10 = calc.calculate_threshold(10)
    t50 = calc.calculate_threshold(50)
    t100 = calc.calculate_threshold(100)

    assert 1.8 > t10 > t50 > t100 > 0.1


def test_dynamic_entropy_adult_transition_rigorous_decay():
    """Adult transition must decay faster (higher decay constant k=0.15 vs 0.05)."""
    calc = DynamicEntropyCalculator(e_max=1.8, e_ideal=0.1)

    t_standard = calc.calculate_threshold(20, is_adult_transition=False)
    t_adult = calc.calculate_threshold(20, is_adult_transition=True)

    assert t_adult < t_standard


def test_dynamic_entropy_clamping():
    """Threshold must strictly remain within [e_ideal, e_max]."""
    calc = DynamicEntropyCalculator(e_max=2.0, e_ideal=0.05)

    # Very large number of episodes
    t_huge = calc.calculate_threshold(10000)
    assert t_huge >= 0.05
    assert math.isclose(t_huge, 0.05, abs_tol=1e-4)
