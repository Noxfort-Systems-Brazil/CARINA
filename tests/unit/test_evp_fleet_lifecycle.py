# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Unit tests for EVP fleet registration and telemetry lifecycle (< 200 lines).
Covers fleet CRUD, online/offline status transitions, and unregistered vehicle filtering.
"""

import time
import pytest

from src.evp.evp_models import CorporationType, RegisteredVehicle, TelemetryData
from src.evp.evp_service import EVPService


@pytest.mark.unit
def test_evp_registered_fleet_management():
    """Validates that fleet starts empty by default and supports manual registration and removal."""
    service = EVPService()

    fleet = service.get_registered_fleet()
    assert len(fleet) == 0

    nova_viatura = RegisteredVehicle(
        vehicle_id="RESGATE-05",
        corporation=CorporationType.BOMBEIRO,
        plate="RES-2026",
        description="Viatura de Desencarceramento",
        is_active=True,
    )
    service.register_fleet_vehicle(nova_viatura)
    assert service.is_vehicle_authorized("RESGATE-05") is True
    assert len(service.get_registered_fleet()) == 1

    all_v = service.get_all_vehicles()
    resgate_entry = next((v for v in all_v if v["vehicle_id"] == "RESGATE-05"), None)
    assert resgate_entry is not None
    assert resgate_entry["is_online"] is False
    assert resgate_entry["status"] == "OFFLINE"
    assert resgate_entry["plate"] == "RES-2026"

    assert service.unregister_fleet_vehicle("RESGATE-05") is True
    assert len(service.get_registered_fleet()) == 0
    assert len(service.get_all_vehicles()) == 0
    assert service.is_vehicle_authorized("RESGATE-05") is False
    assert service.unregister_fleet_vehicle("INEXISTENTE") is False

    # Validates that subsequent telemetry for RESGATE-05 is discarded and does not auto-register
    t_deleted = TelemetryData(
        vehicle_id="RESGATE-05",
        corporation=CorporationType.BOMBEIRO,
        latitude=-23.5505,
        longitude=-46.6333,
        speed_kmh=40.0,
    )
    service.process_telemetry(t_deleted)
    assert len(service.get_all_vehicles()) == 0
    assert service.is_vehicle_authorized("RESGATE-05") is False
    assert service.get_registered_fleet() == []

    # Validates that intentional re-registration enables vehicle normally
    service.register_fleet_vehicle(nova_viatura)
    assert service.is_vehicle_authorized("RESGATE-05") is True
    assert len(service.get_registered_fleet()) == 1


@pytest.mark.unit
def test_evp_vehicle_online_offline_lifecycle_and_reconnection():
    """Validates ONLINE -> OFFLINE status transition and immediate reconnection upon turning on the vehicle."""
    service = EVPService(offline_timeout_seconds=30.0)
    service.register_fleet_vehicle(
        RegisteredVehicle(vehicle_id="SAMU-01", corporation=CorporationType.SAMU)
    )

    # 1. Vehicle sends first signal (engine running) -> ONLINE
    t1 = TelemetryData(
        vehicle_id="SAMU-01",
        corporation=CorporationType.SAMU,
        latitude=-23.5505,
        longitude=-46.6333,
        speed_kmh=50.0,
        siren_active=False,
    )
    service.process_telemetry(t1)

    vehicles = {v["vehicle_id"]: v for v in service.get_all_vehicles()}
    assert vehicles["SAMU-01"]["is_online"] is True
    assert vehicles["SAMU-01"]["status"] == "ONLINE"
    assert vehicles["SAMU-01"]["speed_kmh"] == 50.0

    # 2. Simulates engine off / lack of signal (>30 seconds)
    veh_obj = service._vehicles["SAMU-01"]
    veh_obj.last_update_time = time.time() - 35.0

    vehicles = {v["vehicle_id"]: v for v in service.get_all_vehicles()}
    assert "SAMU-01" in vehicles
    assert vehicles["SAMU-01"]["is_online"] is False
    assert vehicles["SAMU-01"]["status"] == "OFFLINE"

    # 3. Vehicle turns on again and sends new signal at new coordinate -> Returns to ONLINE
    t2 = TelemetryData(
        vehicle_id="SAMU-01",
        corporation=CorporationType.SAMU,
        latitude=-23.5520,
        longitude=-46.6350,
        speed_kmh=62.0,
        siren_active=True,
    )
    service.process_telemetry(t2)

    vehicles = {v["vehicle_id"]: v for v in service.get_all_vehicles()}
    assert vehicles["SAMU-01"]["is_online"] is True
    assert vehicles["SAMU-01"]["status"] == "ONLINE"
    assert vehicles["SAMU-01"]["latitude"] == -23.5520
    assert vehicles["SAMU-01"]["speed_kmh"] == 62.0
    assert vehicles["SAMU-01"]["siren_active"] is True


@pytest.mark.unit
def test_evp_unregistered_telemetry_ignored_hardware_pattern():
    """Ensures Hardware pattern: telemetry received from unregistered vehicles is ignored and not auto-saved."""
    service = EVPService()
    assert service.auto_register_fleet is False
    assert len(service.get_registered_fleet()) == 0

    # Telemetry transmitted by unauthorized / unregistered vehicle
    telemetry = TelemetryData(
        vehicle_id="UNKNOWN-CAR",
        corporation=CorporationType.POLICIA,
        latitude=-23.5505,
        longitude=-46.6333,
        speed_kmh=80.0,
        siren_active=True,
    )
    service.process_telemetry(telemetry)

    # Must not register in database/fleet and must not appear in list
    assert len(service.get_registered_fleet()) == 0
    assert len(service.get_all_vehicles()) == 0
    assert "UNKNOWN-CAR" not in service._vehicles
    assert service.is_vehicle_authorized("UNKNOWN-CAR") is False
