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

# File: tests/unit/test_utmc_modular.py
# Author: Gabriel Moraes
# Date: September 2026

from unittest.mock import MagicMock

import pytest

from src.drivers.utmc_action_executor import UtmcActionExecutor
from src.drivers.utmc_config import UtmcConfig
from src.drivers.utmc_driver import UtmcDriver
from src.drivers.utmc_stage_mapper import UtmcStageMapper
from src.drivers.utmc_telemetry import UtmcTelemetryCollector

# =============================================================================
# 1. UtmcConfig Unit Tests (SRP & DIP)
# =============================================================================


@pytest.mark.unit
def test_utmc_config_loads_from_dict():
    raw_data = {
        "stage_control": {"hold": "1.3.6.1.4.1.2825.4.2.1.1.4.1.2.1", "force_off": "1.3.6.1.4.1.2825.4.2.1.1.4.1.3.1"},
        "telemetry": {
            "status_active": "1.3.6.1.4.1.2825.4.2.1.1.4.1.4.1",
            "status_demand": "1.3.6.1.4.1.2825.4.2.1.1.4.1.5.1",
        },
        "system": {"flash": "1.3.6.1.4.1.2825.4.2.1.1.2.1.255.1", "watchdog": "1.3.6.1.4.1.2825.4.2.1.1.2.1.21.1"},
    }
    config = UtmcConfig(config_dict=raw_data)
    assert config.get_stage_oid("hold") == "1.3.6.1.4.1.2825.4.2.1.1.4.1.2.1"
    assert config.get_telemetry_oid("status_active") == "1.3.6.1.4.1.2825.4.2.1.1.4.1.4.1"
    assert config.get_system_oid("watchdog") == "1.3.6.1.4.1.2825.4.2.1.1.2.1.21.1"


@pytest.mark.unit
def test_utmc_config_fallback_on_missing_file():
    config = UtmcConfig(config_path="/non/existent/utmc.json")
    assert config.get_stage_oid("hold") is None
    assert config.get_telemetry_oid("status_active") is None


# =============================================================================
# 2. UtmcStageMapper Unit Tests (SRP & OCP)
# =============================================================================


@pytest.mark.unit
def test_utmc_stage_mapper_bitshift():
    mapper = UtmcStageMapper()
    # Stage index 0 -> 1 << 0 = 1
    assert mapper.convert_stage_to_hardware_mask(0) == 1
    # Stage index 1 -> 1 << 1 = 2
    assert mapper.convert_stage_to_hardware_mask(1) == 2
    # Stage index 2 -> 1 << 2 = 4
    assert mapper.convert_stage_to_hardware_mask(2) == 4
    # With stage codes dict
    assert mapper.convert_stage_to_hardware_mask(3, stage_codes={3: "GgOrrOGGO"}) == 8


# =============================================================================
# 3. UtmcActionExecutor Unit Tests (SRP & OCP)
# =============================================================================


@pytest.mark.unit
def test_utmc_action_executor_standard_actions():
    mock_snmp_set = MagicMock(return_value=(True, "OK"))
    config = UtmcConfig(
        config_dict={
            "stage_control": {"hold": "OID_HOLD", "force_off": "OID_FORCE_OFF", "extend": "OID_EXTEND"},
            "telemetry": {"status_demand": "OID_DEMAND"},
            "system": {"flash": "OID_FLASH", "dark": "OID_DARK"},
        }
    )
    executor = UtmcActionExecutor(snmp_set_fn=mock_snmp_set, config=config, ip_address="10.0.0.2")

    # 1. Flash
    assert executor.execute({"action_type": "flash"}) is True
    mock_snmp_set.assert_called_with("OID_FLASH", 1)

    # 2. Hold with stage
    assert executor.execute({"action_type": "hold", "stage": 3}) is True
    # Stage 3 -> bitmask 1 << (3-1) = 4
    mock_snmp_set.assert_called_with("OID_HOLD", 4)

    # 3. Extend
    assert executor.execute({"action_type": "extend", "stage": 2}) is True
    # Stage 2 -> bitmask 1 << 1 = 2
    mock_snmp_set.assert_called_with("OID_EXTEND", 2)

    # 4. Demand / Veh call
    assert executor.execute({"action_type": "demand", "stage": 1}) is True
    mock_snmp_set.assert_called_with("OID_DEMAND", 1)


@pytest.mark.unit
def test_utmc_action_executor_extensibility_ocp():
    mock_snmp_set = MagicMock(return_value=(True, "OK"))
    config = UtmcConfig(config_dict={})
    executor = UtmcActionExecutor(snmp_set_fn=mock_snmp_set, config=config)

    # Custom action registered dynamically (OCP)
    def custom_bus_priority_handler(action_data, bitmask):
        return mock_snmp_set("OID_BUS_PRIORITY", 1)

    executor.register_handler("bus_priority", custom_bus_priority_handler)

    assert executor.execute({"action_type": "bus_priority"}) is True
    mock_snmp_set.assert_called_with("OID_BUS_PRIORITY", 1)


# =============================================================================
# 4. UtmcTelemetryCollector Unit Tests (SRP)
# =============================================================================


@pytest.mark.unit
def test_utmc_telemetry_collector_success():
    config = UtmcConfig(
        config_dict={
            "telemetry": {"status_active": "OID_ACT", "status_leaving": "OID_LEAV", "status_ped_demand": "OID_PED"}
        }
    )

    def mock_snmp_get(oid):
        data = {"OID_ACT": (True, "4"), "OID_LEAV": (True, "2"), "OID_PED": (True, "1")}
        return data.get(oid, (False, "OID not found"))

    collector = UtmcTelemetryCollector(snmp_get_fn=mock_snmp_get, config=config)
    telemetry = collector.collect()

    assert telemetry["protocol"] == "UTMC2"
    assert telemetry["status"] == "online"
    assert telemetry["active_greens"] == 4
    assert telemetry["active_yellows"] == 2
    assert telemetry["active_ped_calls"] == 1


@pytest.mark.unit
def test_utmc_telemetry_collector_offline():
    config = UtmcConfig(config_dict={"telemetry": {}})
    mock_snmp_get = MagicMock(return_value=(False, "TIMEOUT"))
    collector = UtmcTelemetryCollector(snmp_get_fn=mock_snmp_get, config=config)
    telemetry = collector.collect()

    assert telemetry["status"] == "offline"
    assert telemetry["active_greens"] == 0


# =============================================================================
# 5. UtmcDriver Facade Integration Unit Tests
# =============================================================================


@pytest.mark.unit
def test_utmc_driver_facade_coordination():
    driver = UtmcDriver(ip_address="127.0.0.1", port=161, intersection_id="J_UTMC_SOLID_TEST")
    driver.snmp_set = MagicMock(return_value=(True, "OK"))
    driver.snmp_get = MagicMock(return_value=(True, "2"))

    # Protocol name
    assert driver.get_protocol_name() == "UTMC2"

    # Properties pass-through
    assert isinstance(driver.oids, dict)

    # Logical action: NEXT_STAGE
    success_next = driver.apply_logical_action(action=0, current_stage_idx=0, green_stages=[0, 1])
    assert success_next is True

    # Logical action: HOLD
    success_hold = driver.apply_logical_action(action=1, current_stage_idx=0, green_stages=[0, 1])
    assert success_hold is True

    # Heartbeat
    success_hb = driver.send_heartbeat_pulse()
    assert success_hb is True

    # Release control
    success_release = driver.release_control()
    assert success_release is True
