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

# File: tests/unit/test_manual_override_hft.py
# Author: Gabriel Moraes
# Date: September 2026

import configparser
from unittest.mock import MagicMock

import pytest

from src.engine.action_supervisor import ActionSupervisor


@pytest.mark.unit
def test_action_supervisor_manual_override():
    # Setup mock connections
    connection_manager = MagicMock()
    settings = configparser.ConfigParser()
    state_extractor = MagicMock()
    locale_manager = MagicMock()

    driver = MagicMock()
    connection_manager.active_connections = {"J1": driver}

    # Initialize ActionSupervisor
    supervisor = ActionSupervisor(
        connection_manager=connection_manager,
        settings=settings,
        state_extractor=state_extractor,
        locale_manager=locale_manager,
    )

    # Apply override ALERT
    supervisor.apply_hardware_override("J1", "ALERT")
    assert supervisor.override_states["J1"] == "ALERT"
    driver.apply_action.assert_called_with({"action_type": "flash"})
    driver.log_carina_override.assert_called_with("ALERT")

    # Test send_stage_hold is skipped during override
    driver.reset_mock()
    supervisor.send_stage_hold("J1", 0)
    driver.apply_action.assert_not_called()

    # Apply override OFF
    supervisor.apply_hardware_override("J1", "OFF")
    assert supervisor.override_states["J1"] == "OFF"
    driver.apply_action.assert_called_with({"action_type": "dark"})
    driver.log_carina_override.assert_called_with("OFF")

    # Return to NORMAL
    driver.reset_mock()
    supervisor.apply_hardware_override("J1", "NORMAL")
    assert "J1" not in supervisor.override_states
    driver.apply_action.assert_called_with({"action_type": "release_dark"})
