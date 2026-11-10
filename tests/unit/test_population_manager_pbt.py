# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Unit tests for Intra-Phase Population-Based Training (PBT).
"""

from unittest.mock import MagicMock
import pytest

from core.enums import Maturity
from core.population_manager import PopulationManager


class MockPolicyNet:
    def __init__(self, val: float = 1.0):
        self.val = val

    def state_dict(self):
        return {"val": self.val}

    def load_state_dict(self, state_dict):
        self.val = state_dict["val"]


class MismatchedPolicyNet(MockPolicyNet):
    def load_state_dict(self, state_dict):
        raise RuntimeError("Size mismatch: target layer has 4 neurons, source has 2.")


class MockAgent:
    def __init__(self, agent_id: str, val: float = 1.0, is_mismatched: bool = False):
        self.agent_id = agent_id
        self.policy_net = MismatchedPolicyNet(val) if is_mismatched else MockPolicyNet(val)
        self.hyperparams = {
            "learning_rate": 0.001,
            "dropout_p": 0.1,
            "regularization_alpha": 0.01,
        }
        self.update_hyperparameters = MagicMock()


@pytest.fixture
def mock_pbt_setup():
    mock_settings = MagicMock()
    mock_settings.has_section.return_value = True
    mock_settings.__getitem__.return_value = {
        "evolution_frequency_episodes": "1",
        "exploitation_percentile": "50",
        "learning_rate_range": "0.0001, 0.01",
        "dropout_p_range": "0.0, 0.5",
        "regularization_alpha_range": "0.001, 0.1",
    }
    mock_lifecycle = MagicMock()
    mock_locale = MagicMock()
    mock_locale.get_string.side_effect = lambda key, **kwargs: f"[{key}]"

    mgr = PopulationManager(mock_settings, mock_lifecycle, mock_locale)
    return mgr


def test_pbt_intra_phase_isolation(mock_pbt_setup):
    """Verifies that TEEN only clones TEEN, ADULT only clones ADULT, and CHILD is protected."""
    mgr = mock_pbt_setup

    c1 = MockAgent("child_1", val=100.0)
    c2 = MockAgent("child_2", val=90.0)
    t1 = MockAgent("teen_1", val=20.0)
    t2 = MockAgent("teen_2", val=5.0)
    a1 = MockAgent("adult_1", val=50.0)
    a2 = MockAgent("adult_2", val=10.0)

    mgr.agents = {
        "child_1": c1,
        "child_2": c2,
        "teen_1": t1,
        "teen_2": t2,
        "adult_1": a1,
        "adult_2": a2,
    }

    maturity_map = {
        "child_1": Maturity.CHILD,
        "child_2": Maturity.CHILD,
        "teen_1": Maturity.TEEN,
        "teen_2": Maturity.TEEN,
        "adult_1": Maturity.ADULT,
        "adult_2": Maturity.ADULT,
    }

    # Child has highest scores (1000, 950), Teen (200, 50), Adult (500, 100)
    mgr.collect_episode_rewards({
        "child_1": 1000.0,
        "child_2": 950.0,
        "teen_1": 200.0,
        "teen_2": 50.0,
        "adult_1": 500.0,
        "adult_2": 100.0,
    })

    mgr.evolve(maturity_map=maturity_map)

    # 1. Child must NOT be mutated or cloned
    assert not c1.update_hyperparameters.called
    assert not c2.update_hyperparameters.called
    assert c2.policy_net.val == 90.0

    # 2. Teen 2 must clone Teen 1 (val becomes 20.0, NOT 100.0 from Child 1)
    assert t2.update_hyperparameters.called
    assert t2.policy_net.val == 20.0

    # 3. Adult 2 must clone Adult 1 (val becomes 50.0, NOT 100.0 from Child 1)
    assert a2.update_hyperparameters.called
    assert a2.policy_net.val == 50.0


def test_pbt_child_cohort_skipped(mock_pbt_setup):
    """Verifies that when all agents are CHILD, evolution is completely skipped."""
    mgr = mock_pbt_setup
    c1 = MockAgent("child_1", val=1.0)
    c2 = MockAgent("child_2", val=2.0)
    mgr.agents = {"child_1": c1, "child_2": c2}

    maturity_map = {"child_1": Maturity.CHILD, "child_2": Maturity.CHILD}
    mgr.collect_episode_rewards({"child_1": 10.0, "child_2": 2.0})

    mgr.evolve(maturity_map=maturity_map)

    assert not c1.update_hyperparameters.called
    assert not c2.update_hyperparameters.called
    assert c1.policy_net.val == 1.0
    assert c2.policy_net.val == 2.0


def test_pbt_tensor_mismatch_safety(mock_pbt_setup):
    """Verifies that an architecture mismatch during weight copy doesn't crash evolution."""
    mgr = mock_pbt_setup

    t1 = MockAgent("teen_1", val=50.0)
    t2 = MockAgent("teen_2", val=10.0, is_mismatched=True)
    mgr.agents = {"teen_1": t1, "teen_2": t2}

    maturity_map = {"teen_1": Maturity.TEEN, "teen_2": Maturity.TEEN}
    mgr.collect_episode_rewards({"teen_1": 100.0, "teen_2": 10.0})

    # Should safely catch RuntimeError without raising:
    mgr.evolve(maturity_map=maturity_map)
    assert t2.policy_net.val == 10.0  # Kept original due to mismatch skip


def test_pbt_legacy_fallback_without_maturity_map(mock_pbt_setup):
    """Verifies that evolve() without maturity_map works as legacy cohort."""
    mgr = mock_pbt_setup

    a1 = MockAgent("a1", val=99.0)
    a2 = MockAgent("a2", val=11.0)
    mgr.agents = {"a1": a1, "a2": a2}
    mgr.collect_episode_rewards({"a1": 100.0, "a2": 10.0})

    mgr.evolve(maturity_map=None)

    assert a2.update_hyperparameters.called
    assert a2.policy_net.val == 99.0
