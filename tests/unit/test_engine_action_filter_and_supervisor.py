# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Noxfort Systems
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

# File: tests/unit/test_engine_action_filter_and_supervisor.py
# Author: Gabriel Moraes
# Date: September 2026

from unittest.mock import MagicMock, patch

import pytest

from core.enums import Maturity
from engine.action_filter import ActionFilter
from engine.action_supervisor import ActionSupervisor


@pytest.fixture
def mock_locale():
    lm = MagicMock()
    lm.get_string.side_effect = lambda key, fallback=None, **kwargs: fallback or key
    return lm


def test_action_filter_normal_approval(mock_locale):
    """ActionFilter permits actions approved by ActionAuthorizer when no override exists."""
    authorizer = MagicMock()
    authorizer.is_action_authorized.return_value = (True, "Authorized")

    maturity_manager = MagicMock()
    maturity_manager.agent_maturity = {"TL_1": Maturity.ADULT}

    filter_module = ActionFilter(authorizer, maturity_manager, mock_locale)

    raw_actions = {"TL_1": 0}
    override_states = {"TL_1": "NORMAL"}

    with patch("core.system_reporter.SystemReporter.report_agent_decision") as mock_report:
        filtered = filter_module.filter_actions(raw_actions, override_states, current_sim_time=12.0)
        assert filtered == {"TL_1": 0}
        assert mock_report.called


def test_action_filter_with_override_state(mock_locale):
    """ActionFilter denies action when traffic light has active override state."""
    authorizer = MagicMock()
    authorizer.is_action_authorized.return_value = (True, "Authorized")

    maturity_manager = MagicMock()
    maturity_manager.agent_maturity = {"TL_1": Maturity.ADULT}

    filter_module = ActionFilter(authorizer, maturity_manager, mock_locale)

    raw_actions = {"TL_1": 0}
    override_states = {"TL_1": "ALERT"}

    filtered = filter_module.filter_actions(raw_actions, override_states, current_sim_time=12.0)
    assert filtered == {}


def test_action_supervisor_init(mock_locale):
    """ActionSupervisor initializes safety rules and empty tracking dictionaries."""
    mock_conn = MagicMock()
    mock_settings = MagicMock()
    mock_extractor = MagicMock()

    supervisor = ActionSupervisor(mock_conn, mock_settings, mock_extractor, mock_locale)
    assert supervisor.vetoed_actions == {}
    assert supervisor.override_states == {}
    assert supervisor.green_time is not None


def test_action_supervisor_veto_handling(mock_locale):
    """ActionSupervisor overrides vetoed action to HOLD (action=1)."""
    mock_conn = MagicMock()
    mock_settings = MagicMock()
    mock_extractor = MagicMock()

    supervisor = ActionSupervisor(mock_conn, mock_settings, mock_extractor, mock_locale)
    supervisor.update_vetos({"TL_1": {"veto_action": 0}})

    actions = {"TL_1": 0}
    supervisor.apply_actions(actions, current_sim_time=10.0, current_stages={})
    assert actions["TL_1"] == 1
    assert "TL_1" not in supervisor.vetoed_actions


def test_action_supervisor_send_stage_hold(mock_locale):
    """ActionSupervisor commands driver to hold stage when no override is present."""
    mock_conn = MagicMock()
    mock_driver = MagicMock()
    mock_conn.active_connections = {"TL_1": mock_driver}

    supervisor = ActionSupervisor(mock_conn, MagicMock(), MagicMock(), mock_locale)
    supervisor.send_stage_hold("TL_1", stage_idx=2)
    assert mock_driver.apply_decision.called or mock_driver.apply_action.called

    # If ALERT override is active, should skip sending
    supervisor.override_states["TL_1"] = "ALERT"
    mock_driver.reset_mock()
    supervisor.send_stage_hold("TL_1", stage_idx=2)
    assert not mock_driver.apply_decision.called
    assert not mock_driver.apply_action.called


def test_action_supervisor_cleanup_and_reset(mock_locale):
    """ActionSupervisor properly cleans up and resets state."""
    mock_conn = MagicMock()
    supervisor = ActionSupervisor(mock_conn, MagicMock(), MagicMock(), mock_locale)

    supervisor.override_states["TL_1"] = "ALERT"
    supervisor.vetoed_actions["TL_1"] = 0
    supervisor.cleanup_intersection("TL_1")
    assert "TL_1" not in supervisor.override_states
    assert "TL_1" not in supervisor.vetoed_actions

    supervisor.override_states["TL_2"] = "OFF"
    supervisor.reset()
    assert supervisor.override_states == {}
