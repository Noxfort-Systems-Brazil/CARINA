# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from unittest.mock import MagicMock, patch

import pytest

from core.decision_coordinator import DecisionCoordinator


def test_decision_coordinator_initialization():
    """Tests initializing DecisionCoordinator with agents and graph topology."""
    mock_agent_1 = MagicMock()
    mock_agent_2 = MagicMock()
    agents = {"TL_1": mock_agent_1, "TL_2": mock_agent_2}
    neighborhoods = {"TL_1": ["TL_2"], "TL_2": ["TL_1"]}

    mock_env = MagicMock()
    mock_strategic = MagicMock()

    coordinator = DecisionCoordinator(
        agents=agents,
        neighborhoods=neighborhoods,
        environment=mock_env,
        strategic_coordinator=mock_strategic,
        message_size=4,
        n_observations=10,
        guardian_agent=None,
    )

    assert coordinator.tl_list == ["TL_1", "TL_2"]
    assert coordinator.tl_to_idx == {"TL_1": 0, "TL_2": 1}
    assert coordinator.adjacency_matrix is not None


def test_decision_coordinator_empty_states():
    """Empty states dictionary must return empty actions immediately."""
    coordinator = DecisionCoordinator(
        agents={},
        neighborhoods={},
        environment=MagicMock(),
        strategic_coordinator=MagicMock(),
        message_size=4,
        n_observations=10,
    )
    actions, decisions = coordinator.get_coordinated_actions(
        current_states={},
        state_history={},
        current_operation_mode="AUTO",
    )
    assert actions == {}
    assert decisions == {}


def test_decision_coordinator_override_state():
    """Manual overrides set on DecisionCoordinator take precedence."""
    mock_agent = MagicMock()
    agents = {"TL_1": mock_agent}
    coordinator = DecisionCoordinator(
        agents=agents,
        neighborhoods={},
        environment=MagicMock(),
        strategic_coordinator=MagicMock(),
        message_size=4,
        n_observations=10,
    )

    coordinator.override_states["TL_1"] = "G"
    assert coordinator.override_states.get("TL_1") == "G"

    del coordinator.override_states["TL_1"]
    assert "TL_1" not in coordinator.override_states
