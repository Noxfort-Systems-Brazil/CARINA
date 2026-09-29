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

# File: tests/fixtures/hardware_fixtures.py
# Author: Gabriel Moraes
# Date: September 2026

from typing import Any

import pytest


@pytest.fixture
def mock_snmp_hardware(monkeypatch):
    """
    Simulates SNMP Hardware without generating network traffic.
    Injects interceptions for snmp_get and snmp_set directly into BaseTrafficDriver.
    """
    from src.drivers.base_driver import BaseTrafficDriver

    hardware_memory = {}

    def fake_snmp_get(self, oid: str):
        if oid in hardware_memory:
            return True, hardware_memory[oid]
        return False, "TIMEOUT (Simulated Timeout)"

    def fake_snmp_set(self, oid: str, value: Any, value_type: Any = None):
        hardware_memory[oid] = value
        return True, "Success"

    monkeypatch.setattr(BaseTrafficDriver, "snmp_get", fake_snmp_get)
    monkeypatch.setattr(BaseTrafficDriver, "snmp_set", fake_snmp_set)

    return hardware_memory


@pytest.fixture
def mock_logger(mocker):
    """
    Simulates a generic log function for components expecting a log callback.
    """
    return mocker.MagicMock()
