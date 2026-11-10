# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

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
