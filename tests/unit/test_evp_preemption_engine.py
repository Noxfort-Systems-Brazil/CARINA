# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Dedicated unit tests for EVPPreemptionEngine preemption engine (<300 lines).
Covers state machine, stage transitions, CONTRAN watchdog, and offline fail-safe.
"""

import time
import pytest

from src.evp.evp_models import CorporationType, EmergencyVehicle
from src.evp.evp_preemption_engine import ACTION_ADVANCE, ACTION_HOLD, EVPPreemptionEngine


@pytest.mark.unit
def test_preemption_engine_stage_actions_and_watchdog():
    """Validates action computation (HOLD vs ADVANCE) and regulatory watchdog of the engine."""
    dispatched = []

    def mock_dispatch(intersection_id, stage, action):
        dispatched.append((intersection_id, stage, action))

    engine = EVPPreemptionEngine(max_dwell_timeout_seconds=45.0, on_action_dispatch=mock_dispatch)

    # 1. No active preemption -> NOMINAL
    act, reason = engine.get_preemption_action("INT_01", current_stage=0)
    assert act == ACTION_HOLD
    assert reason == "NOMINAL"
    assert engine.is_preemption_active("INT_01") is False

    # 2. Activates preemption for vehicle
    vehicle = EmergencyVehicle(
        vehicle_id="SAMU_TEST",
        corporation=CorporationType.SAMU,
        latitude=-23.55,
        longitude=-46.63,
        siren_active=True,
    )
    engine.activate_preemption("INT_01", vehicle, target_stage=1)
    assert engine.is_preemption_active("INT_01") is True
    assert ("INT_01", 1, "ACTIVATE_PREEMPT") in dispatched

    # 3. Stage different from target -> ADVANCE for transition
    vehicles_dict = {"SAMU_TEST": vehicle}
    act, reason = engine.get_preemption_action("INT_01", current_stage=0, vehicles=vehicles_dict)
    assert act == ACTION_ADVANCE
    assert reason == "EVP_TRANSICAO_PARA_ALVO"

    # 4. Target green stage reached -> HOLD to maintain green corridor
    act, reason = engine.get_preemption_action("INT_01", current_stage=1, vehicles=vehicles_dict)
    assert act == ACTION_HOLD
    assert reason == "EVP_CORREDOR_VERDE_HOLD"

    # 5. Watchdog timeout (time >= 45s) -> Automatic release
    engine._active_preemptions["INT_01"]["start_time"] = time.time() - 50.0
    act, reason = engine.get_preemption_action("INT_01", current_stage=1, vehicles=vehicles_dict)
    assert act == ACTION_ADVANCE
    assert reason == "EVP_WATCHDOG_TIMEOUT_EXCEEDED"
    assert engine.is_preemption_active("INT_01") is False


@pytest.mark.unit
def test_preemption_engine_offline_vehicle_failsafe():
    """Validates that a vehicle going offline immediately disarms the traffic light."""
    engine = EVPPreemptionEngine()
    vehicle = EmergencyVehicle(
        vehicle_id="BOMBEIRO_01",
        corporation=CorporationType.BOMBEIRO,
        latitude=-23.55,
        longitude=-46.63,
        siren_active=True,
        offline_timeout_seconds=30.0,
    )
    engine.activate_preemption("INT_SAFE", vehicle, target_stage=2)
    assert engine.is_preemption_active("INT_SAFE") is True

    # Simulates signal loss (>30s)
    vehicle.last_update_time = time.time() - 40.0
    assert vehicle.is_online is False

    vehicles_dict = {"BOMBEIRO_01": vehicle}
    act, reason = engine.get_preemption_action("INT_SAFE", current_stage=2, vehicles=vehicles_dict)
    assert act == ACTION_ADVANCE
    assert reason == "EVP_VEHICLE_OFFLINE_FAILSAFE"
    assert engine.is_preemption_active("INT_SAFE") is False


@pytest.mark.unit
def test_preemption_engine_siren_off_releases_all_intersections():
    """Validates that turning off Alert Mode (siren_active=False) disarms all intersections associated with vehicle."""
    engine = EVPPreemptionEngine()
    vehicle = EmergencyVehicle(
        vehicle_id="SAMU_MULTI",
        corporation=CorporationType.SAMU,
        latitude=-23.55,
        longitude=-46.63,
        siren_active=True,
    )

    # Simulates vehicle activating preemption at 2 consecutive intersections
    engine.activate_preemption("INT_A", vehicle, target_stage=1)
    engine.activate_preemption("INT_B", vehicle, target_stage=2)
    assert engine.is_preemption_active("INT_A") is True
    assert engine.is_preemption_active("INT_B") is True
    assert "INT_A" in vehicle.active_intersections
    assert "INT_B" in vehicle.active_intersections

    # Deactivates Alert Mode (siren turned off)
    vehicle.siren_active = False

    class MockTopology:
        intersections_geo = {}

    class MockKinematics:
        pass

    engine.evaluate_vehicle_lifecycle(vehicle, MockTopology(), MockKinematics())

    # Both intersections should have been released
    assert engine.is_preemption_active("INT_A") is False
    assert engine.is_preemption_active("INT_B") is False
    assert vehicle.is_evp_triggered is False
    assert len(vehicle.active_intersections) == 0


@pytest.mark.unit
def test_preemption_engine_siren_inactive_in_get_preemption_action():
    """Validates disarm in get_preemption_action when vehicle turns off siren."""
    engine = EVPPreemptionEngine()
    vehicle = EmergencyVehicle(
        vehicle_id="POLICIA_01",
        corporation=CorporationType.POLICIA,
        latitude=-23.55,
        longitude=-46.63,
        siren_active=True,
    )
    engine.activate_preemption("INT_POL", vehicle, target_stage=1)
    assert engine.is_preemption_active("INT_POL") is True

    # Turns off siren but remains online
    vehicle.siren_active = False
    vehicles_dict = {"POLICIA_01": vehicle}

    act, reason = engine.get_preemption_action("INT_POL", current_stage=1, vehicles=vehicles_dict)
    assert act == ACTION_ADVANCE
    assert reason == "EVP_SIREN_INACTIVE_RELEASE"
    assert engine.is_preemption_active("INT_POL") is False


@pytest.mark.unit
def test_preemption_engine_unconditional_watchdog_timeout():
    """Validates that CONTRAN watchdog disarms even if traffic light is in different stage from target."""
    engine = EVPPreemptionEngine(max_dwell_timeout_seconds=45.0)
    vehicle = EmergencyVehicle(
        vehicle_id="SAMU_DWELL",
        corporation=CorporationType.SAMU,
        latitude=-23.55,
        longitude=-46.63,
        siren_active=True,
    )
    engine.activate_preemption("INT_DWELL", vehicle, target_stage=1)
    engine._active_preemptions["INT_DWELL"]["start_time"] = time.time() - 50.0

    # current_stage=0 != target_stage=1 (traffic light still held in previous stage)
    vehicles_dict = {"SAMU_DWELL": vehicle}
    act, reason = engine.get_preemption_action("INT_DWELL", current_stage=0, vehicles=vehicles_dict)
    assert act == ACTION_ADVANCE
    assert reason == "EVP_WATCHDOG_TIMEOUT_EXCEEDED"
    assert engine.is_preemption_active("INT_DWELL") is False

