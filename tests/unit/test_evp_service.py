# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Unit tests for the central EVPService orchestrator (< 200 lines).
Covers traffic evaluation, siren triggers, fail-safe, and safety interception.
"""

import time
import pytest

from src.evp.evp_models import CorporationType, EmergencyVehicle, RegisteredVehicle, TelemetryData
from src.evp.evp_kinematics import EVPKinematicsEngine
from src.evp.evp_service import EVPService, ACTION_ADVANCE, ACTION_HOLD
from src.evp.evp_bridge import EVPBridge


@pytest.mark.unit
def test_evp_stage_action_evaluation():
    """Validates traffic action evaluation (HOLD / ADVANCE) and EVPService watchdog."""
    service = EVPService(max_dwell_timeout_seconds=45.0)
    service.register_intersection("INT_TEST_EVAL", lat=-23.55, lon=-46.63, target_stage=1)

    # 1. No active preemption -> NOMINAL (HOLD=1)
    act, reason = service.get_preemption_action("INT_TEST_EVAL", current_stage=0)
    assert act == ACTION_HOLD
    assert reason == "NOMINAL"

    # Activates preemption with test vehicle
    vehicle = EmergencyVehicle(
        vehicle_id="V_EVAL",
        corporation=CorporationType.SAMU,
        latitude=-23.55,
        longitude=-46.63,
        siren_active=True,
    )
    service.activate_preemption("INT_TEST_EVAL", vehicle)

    # 2. In diverging stage (0 != 1) -> Orders ADVANCE (0) for safe CARINA transition
    act, reason = service.get_preemption_action("INT_TEST_EVAL", current_stage=0)
    assert act == ACTION_ADVANCE
    assert reason == "EVP_TRANSICAO_PARA_ALVO"

    # 3. In target green stage (1 == 1) -> Orders HOLD (1) to keep corridor open
    act, reason = service.get_preemption_action("INT_TEST_EVAL", current_stage=1)
    assert act == ACTION_HOLD
    assert reason == "EVP_CORREDOR_VERDE_HOLD"

    # 4. Simulates watchdog timeout (dwell >= 45s)
    service._active_preemptions["INT_TEST_EVAL"]["start_time"] = time.time() - 50.0
    act, reason = service.get_preemption_action("INT_TEST_EVAL", current_stage=1)
    assert act == ACTION_ADVANCE
    assert reason == "EVP_WATCHDOG_TIMEOUT_EXCEEDED"
    assert service.is_preemption_active("INT_TEST_EVAL") is False


@pytest.mark.unit
def test_evp_service_two_factor_trigger():
    """Validates two-factor trigger activation (Siren + Block Entrance) and immediate release."""
    dispatched_actions = []

    def mock_dispatch(int_id, action, reason):
        dispatched_actions.append((int_id, action, reason))

    service = EVPService(
        kinematics=EVPKinematicsEngine(block_entry_min_meters=60.0, block_entry_max_meters=160.0),
        on_action_dispatch=mock_dispatch,
    )
    service.register_fleet_vehicle(
        RegisteredVehicle(vehicle_id="SAMU_99", corporation=CorporationType.SAMU)
    )

    int_lat, int_lon = -23.550520, -46.633308
    service.register_intersection("INT_01", lat=int_lat, lon=int_lon, target_stage=1)

    lat_200m = int_lat + (200.0 / 111139.0)
    lat_100m = int_lat + (100.0 / 111139.0)

    # Scenario 1: Siren on, but distant (>160m) -> Must not activate preemption
    t_distante = TelemetryData(
        vehicle_id="SAMU_99",
        corporation=CorporationType.SAMU,
        latitude=lat_200m,
        longitude=int_lon,
        speed_kmh=60.0,
        heading_deg=180.0,
        siren_active=True,
    )
    service.process_telemetry(t_distante)
    assert service.is_preemption_active("INT_01") is False

    # Scenario 2: At block entrance (100m), but siren OFF -> Must not activate preemption
    t_sem_sirene = TelemetryData(
        vehicle_id="SAMU_99",
        corporation=CorporationType.SAMU,
        latitude=lat_100m,
        longitude=int_lon,
        speed_kmh=60.0,
        heading_deg=180.0,
        siren_active=False,
    )
    service.process_telemetry(t_sem_sirene)
    assert service.is_preemption_active("INT_01") is False

    # Scenario 3: At block entrance (100m) AND siren ON -> MUST ACTIVATE PREEMPTION!
    t_ativacao = TelemetryData(
        vehicle_id="SAMU_99",
        corporation=CorporationType.SAMU,
        latitude=lat_100m,
        longitude=int_lon,
        speed_kmh=60.0,
        heading_deg=180.0,
        siren_active=True,
    )
    service.process_telemetry(t_ativacao)
    assert service.is_preemption_active("INT_01") is True
    assert len(dispatched_actions) > 0

    # Scenario 4: Siren turned off by operator -> IMMEDIATE RELEASE!
    t_desarme_sirene = TelemetryData(
        vehicle_id="SAMU_99",
        corporation=CorporationType.SAMU,
        latitude=lat_100m,
        longitude=int_lon,
        speed_kmh=60.0,
        heading_deg=180.0,
        siren_active=False,
    )
    service.process_telemetry(t_desarme_sirene)
    assert service.is_preemption_active("INT_01") is False


@pytest.mark.unit
def test_evp_bridge_safety_auditor_interception():
    """Validates SafetyAuditor interception by EVPBridge during preemption."""
    service = EVPService()
    service.register_intersection("INT_TEST", lat=-23.55, lon=-46.63, target_stage=1)

    bridge = EVPBridge(evp_service=service)

    # 1. No active preemption -> No interception
    action, is_evp, reason = bridge.intercept_safety_audit(
        tl_id="INT_TEST",
        current_stage=0,
        stage_duration=10.0,
        suggested_action=0,
    )
    assert is_evp is False
    assert action is None

    # 2. Manually activate preemption at intersection
    test_vehicle = EmergencyVehicle(
        vehicle_id="TEST_CAR",
        corporation=CorporationType.SAMU,
        latitude=-23.55,
        longitude=-46.63,
        siren_active=True,
    )
    service.activate_preemption("INT_TEST", test_vehicle)

    # 3. With active preemption and current stage at target green (1) -> Force HOLD (1)
    action, is_evp, reason = bridge.intercept_safety_audit(
        tl_id="INT_TEST",
        current_stage=1,
        stage_duration=10.0,
        suggested_action=0,
    )
    assert is_evp is True
    assert action == ACTION_HOLD


@pytest.mark.unit
def test_evp_offline_failsafe_preemption_release():
    """Validates automatic preemption release (fail-safe) if vehicle turns off mid-service."""
    service = EVPService(offline_timeout_seconds=30.0)
    service.register_intersection("INT_FAILSAFE", lat=-23.55, lon=-46.63, target_stage=1)

    veh = EmergencyVehicle(
        vehicle_id="SAMU-02",
        corporation=CorporationType.SAMU,
        latitude=-23.55,
        longitude=-46.63,
        siren_active=True,
        offline_timeout_seconds=30.0,
    )
    service._vehicles["SAMU-02"] = veh
    service.activate_preemption("INT_FAILSAFE", veh)
    assert service.is_preemption_active("INT_FAILSAFE") is True

    veh.last_update_time = time.time() - 40.0
    assert veh.is_online is False

    act, reason = service.get_preemption_action("INT_FAILSAFE", current_stage=1)
    assert act == ACTION_ADVANCE
    assert reason == "EVP_VEHICLE_OFFLINE_FAILSAFE"
    assert service.is_preemption_active("INT_FAILSAFE") is False
