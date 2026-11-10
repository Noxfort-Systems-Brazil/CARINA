# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import math

import pytest

from core.dynamic_entropy_calculator import DynamicEntropyCalculator


def test_dynamic_entropy_zero_or_negative_episodes():
    """Zero or negative configured episodes must return the maximum ceiling ln(n_actions)."""
    calc = DynamicEntropyCalculator(n_actions=3, e_ideal=0.1)
    expected_max = math.log(3)
    assert math.isclose(calc.calculate_threshold(0), expected_max, rel_tol=1e-6)
    assert math.isclose(calc.calculate_threshold(-5), expected_max, rel_tol=1e-6)


def test_dynamic_entropy_impossible_ceiling_clamped():
    """Any e_max higher than theoretical maximum entropy ln(n_actions) must be clamped."""
    calc = DynamicEntropyCalculator(n_actions=3, e_max=1.8, e_ideal=0.1)
    expected_max = math.log(3)
    # 1.8 was impossible because max entropy for 3 actions is ln(3) ~ 1.0986
    assert math.isclose(calc.e_max, expected_max, rel_tol=1e-6)
    assert math.isclose(calc.calculate_threshold(0), expected_max, rel_tol=1e-6)


def test_dynamic_entropy_random_policy_rejected():
    """A completely random policy (H = ln(3)) must never pass threshold for any episode t >= 1."""
    calc = DynamicEntropyCalculator(n_actions=3, e_ideal=0.1)
    random_policy_entropy = math.log(3)

    for ep in [1, 3, 5, 10, 20, 50]:
        threshold = calc.calculate_threshold(ep)
        # Random policy entropy should be strictly GREATER than threshold (cannot pass)
        assert random_policy_entropy > threshold, f"Random policy incorrectly passed at episode {ep}: {random_policy_entropy} <= {threshold}"


def test_dynamic_entropy_decay_curve():
    """Threshold should decay toward e_ideal as configured episodes increase."""
    calc = DynamicEntropyCalculator(n_actions=3, e_ideal=0.1)
    max_h = math.log(3)

    t10 = calc.calculate_threshold(10)
    t50 = calc.calculate_threshold(50)
    t100 = calc.calculate_threshold(100)

    assert max_h > t10 > t50 > t100 > 0.1


def test_dynamic_entropy_adult_transition_rigorous_decay():
    """Adult transition must decay faster (higher decay constant k=0.15 vs 0.05)."""
    calc = DynamicEntropyCalculator(n_actions=3, e_ideal=0.1)

    t_standard = calc.calculate_threshold(20, is_adult_transition=False)
    t_adult = calc.calculate_threshold(20, is_adult_transition=True)

    assert t_adult < t_standard
    # At 20 episodes, teen->adult threshold converges close to nominal 0.15
    assert math.isclose(t_adult, 0.15, abs_tol=0.01)


def test_dynamic_entropy_clamping():
    """Threshold must strictly remain within [e_ideal, e_max]."""
    calc = DynamicEntropyCalculator(n_actions=4, e_max=2.0, e_ideal=0.05)

    # Very large number of episodes
    t_huge = calc.calculate_threshold(10000)
    assert t_huge >= 0.05
    assert math.isclose(t_huge, 0.05, abs_tol=1e-4)


def test_dynamic_entropy_normalized_mode():
    """When normalize=True, threshold operates in [e_ideal, 1.0]."""
    calc = DynamicEntropyCalculator(n_actions=3, normalize=True, e_ideal=0.05)
    assert math.isclose(calc.e_max, 1.0)
    assert math.isclose(calc.calculate_threshold(0), 1.0)

    t20 = calc.calculate_threshold(20)
    assert 1.0 > t20 > 0.05


def test_dynamic_entropy_normalize_method():
    """normalize_entropy properly maps raw entropy to [0.0, 1.0]."""
    calc = DynamicEntropyCalculator(n_actions=3)
    assert math.isclose(calc.normalize_entropy(math.log(3)), 1.0)
    assert math.isclose(calc.normalize_entropy(0.0), 0.0)
    assert math.isclose(calc.normalize_entropy(math.log(3) / 2.0), 0.5)
