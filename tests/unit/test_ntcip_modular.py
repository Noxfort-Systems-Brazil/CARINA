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

# File: tests/unit/test_ntcip_modular.py
# Author: Gabriel Moraes
# Date: September 2026

from unittest.mock import MagicMock, patch

import pytest

from src.drivers.ntcip_action_executor import NtcipActionExecutor
from src.drivers.ntcip_config import NtcipConfig
from src.drivers.ntcip_driver import NtcipDriver
from src.drivers.ntcip_stage_mapper import NtcipStageMapper
from src.drivers.ntcip_telemetry import NtcipTelemetryCollector

# =============================================================================
# 1. NtcipConfig Unit Tests (SRP & DIP)
# =============================================================================


@pytest.mark.unit
def test_ntcip_config_loads_from_dict():
    raw_data = {
        "phase_control": {"hold": "1.3.6.1.4.1.1206.4.2.1.1.4.1.2.1", "force_off": "1.3.6.1.4.1.1206.4.2.1.1.4.1.3.1"},
        "telemetry": {"status_greens": "1.3.6.1.4.1.1206.4.2.1.1.4.1.4.1"},
        "system": {"flash": "1.3.6.1.4.1.1206.4.2.1.1.2.1.255.1", "heartbeat": "1.3.6.1.4.1.1206.4.2.1.1.2.1.21.1"},
        "stage_to_phase_map": {"1": 34, "2": 136},
    }
    config = NtcipConfig(config_dict=raw_data)
    assert config.get_phase_oid("hold") == "1.3.6.1.4.1.1206.4.2.1.1.4.1.2.1"
    assert config.get_telemetry_oid("status_greens") == "1.3.6.1.4.1.1206.4.2.1.1.4.1.4.1"
    assert config.get_system_oid("flash") == "1.3.6.1.4.1.1206.4.2.1.1.2.1.255.1"
    assert config.stage_to_phase_map == {1: 34, 2: 136}


@pytest.mark.unit
def test_ntcip_config_fallback_on_missing_file():
    config = NtcipConfig(config_path="/non/existent/path.json")
    assert config.get_phase_oid("hold") is None
    assert config.stage_to_phase_map == {}


# =============================================================================
# 2. NtcipStageMapper Unit Tests (SRP & OCP)
# =============================================================================


@pytest.mark.unit
def test_ntcip_stage_mapper_hardcoded_4_stages():
    mapper = NtcipStageMapper(default_stage_to_phase_map={1: 34, 2: 136, 3: 17, 4: 68})
    # For a 4-stage intersection, stage_idx 0 (stage 1) should map to 34
    mask = mapper.convert_stage_to_hardware_mask(stage_idx=0, green_stages=[0, 1, 2, 3])
    assert mask == 34

    # Stage index 2 (stage 3) maps to 17
    mask = mapper.convert_stage_to_hardware_mask(stage_idx=2, green_stages=[0, 1, 2, 3])
    assert mask == 17


@pytest.mark.unit
def test_ntcip_stage_mapper_dynamic_state_strings():
    mapper = NtcipStageMapper()
    stage_codes = {
        0: "GgOrrOGGO",  # indices 0, 1, 6, 7 -> bits 0, 1, 6, 7 = 1 + 2 + 64 + 128 = 195
        1: "rrrGGgGrr",  # indices 3, 4, 5, 6 -> bits 3, 4, 5, 6 = 8 + 16 + 32 + 64 = 120
        2: "rrrrrrrrr",  # all red -> 0
    }
    # With 5 stages, bypasses 4-stage hardcoded map
    mask_0 = mapper.convert_stage_to_hardware_mask(0, green_stages=[0, 1, 2, 3, 4], stage_codes=stage_codes)
    assert mask_0 == 195

    mask_1 = mapper.convert_stage_to_hardware_mask(1, green_stages=[0, 1, 2, 3, 4], stage_codes=stage_codes)
    assert mask_1 == 120

    mask_2 = mapper.convert_stage_to_hardware_mask(2, green_stages=[0, 1, 2, 3, 4], stage_codes=stage_codes)
    assert mask_2 == 0


@pytest.mark.unit
def test_ntcip_stage_mapper_fallback_bitshift():
    mapper = NtcipStageMapper()
    # No stage_codes provided, fallback is (1 << stage_idx)
    mask = mapper.convert_stage_to_hardware_mask(3, green_stages=[0, 1, 2, 3, 4])
    assert mask == (1 << 3)  # 8


# =============================================================================
# 3. NtcipActionExecutor Unit Tests (SRP & OCP)
# =============================================================================


@pytest.mark.unit
def test_ntcip_action_executor_standard_actions():
    mock_snmp_set = MagicMock(return_value=(True, "OK"))
    config = NtcipConfig(
        config_dict={
            "phase_control": {"hold": "OID_HOLD", "force_off": "OID_FORCE_OFF"},
            "system": {"flash": "OID_FLASH"},
        }
    )
    executor = NtcipActionExecutor(snmp_set_fn=mock_snmp_set, config=config, ip_address="10.0.0.1")

    # 1. Flash
    assert executor.execute({"action_type": "flash"}) is True
    mock_snmp_set.assert_called_with("OID_FLASH", 1)

    # 2. Release Flash
    assert executor.execute({"action_type": "release_flash"}) is True
    mock_snmp_set.assert_called_with("OID_FLASH", 0)

    # 3. Hold with stage_mask
    assert executor.execute({"action_type": "hold", "stage_mask": 42}) is True
    mock_snmp_set.assert_called_with("OID_HOLD", 42)


@pytest.mark.unit
def test_ntcip_action_executor_extensibility_ocp():
    mock_snmp_set = MagicMock(return_value=(True, "OK"))
    config = NtcipConfig(config_dict={})
    executor = NtcipActionExecutor(snmp_set_fn=mock_snmp_set, config=config)

    # Custom action registered dynamically without modifying executor source code (OCP)
    def custom_emergency_handler(action_data, bitmask):
        return mock_snmp_set("OID_CUSTOM_EMERGENCY", 99)

    executor.register_handler("emergency_override", custom_emergency_handler)

    assert executor.execute({"action_type": "emergency_override"}) is True
    mock_snmp_set.assert_called_with("OID_CUSTOM_EMERGENCY", 99)


# =============================================================================
# 4. NtcipTelemetryCollector Unit Tests (SRP)
# =============================================================================


@pytest.mark.unit
def test_ntcip_telemetry_collector_success():
    config = NtcipConfig(
        config_dict={
            "telemetry": {
                "status_greens": "OID_G",
                "status_yellows": "OID_Y",
                "status_reds": "OID_R",
                "status_ped_calls": "OID_P",
            }
        }
    )

    def mock_snmp_get(oid):
        data = {"OID_G": (True, "17"), "OID_Y": (True, "2"), "OID_R": (True, "0"), "OID_P": (True, "4")}
        return data.get(oid, (False, "OID not found"))

    collector = NtcipTelemetryCollector(snmp_get_fn=mock_snmp_get, config=config)
    telemetry = collector.collect()

    assert telemetry["protocol"] == "NTCIP 1202"
    assert telemetry["status"] == "online"
    assert telemetry["active_greens"] == 17
    assert telemetry["active_yellows"] == 2
    assert telemetry["active_reds"] == 0
    assert telemetry["active_ped_calls"] == 4


@pytest.mark.unit
def test_ntcip_telemetry_collector_offline():
    config = NtcipConfig(config_dict={"telemetry": {}})
    mock_snmp_get = MagicMock(return_value=(False, "TIMEOUT"))
    collector = NtcipTelemetryCollector(snmp_get_fn=mock_snmp_get, config=config)
    telemetry = collector.collect()

    assert telemetry["status"] == "offline"
    assert telemetry["active_greens"] == 0


# =============================================================================
# 5. NtcipDriver Facade Integration Unit Tests
# =============================================================================


@pytest.mark.unit
def test_ntcip_driver_facade_coordination():
    driver = NtcipDriver(ip_address="127.0.0.1", port=161, intersection_id="J_SOLID_TEST")
    driver.snmp_set = MagicMock(return_value=(True, "OK"))
    driver.snmp_get = MagicMock(return_value=(True, "34"))

    # Protocol name
    assert driver.get_protocol_name() == "NTCIP 1202"

    # Properties pass-through
    assert isinstance(driver.oids, dict)
    assert isinstance(driver.stage_to_phase_map, dict)

    # Logical action: HOLD
    success_hold = driver.apply_logical_action(
        action=1, current_stage_idx=0, green_stages=[0, 1], stage_codes={0: "GgOrrOGGO"}
    )
    assert success_hold is True

    # Heartbeat
    success_hb = driver.send_heartbeat_pulse()
    assert success_hb is True

    # Release control
    success_release = driver.release_control()
    assert success_release is True
