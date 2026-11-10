# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest

from src.evp.evp_kinematics import EVPKinematicsEngine
from src.evp.evp_models import CorporationType, EmergencyVehicle, TelemetryData


@pytest.mark.unit
def test_corporation_type_and_models():
    """Validates corporation identification and data models."""
    assert CorporationType.from_string("samu") == CorporationType.SAMU
    assert CorporationType.from_string("bombeiro") == CorporationType.BOMBEIROS
    assert CorporationType.from_string("policia") == CorporationType.POLICIA
    assert CorporationType.from_string("outro") == CorporationType.POLICIA

    telemetry = TelemetryData(
        vehicle_id="SAMU_01",
        corporation=CorporationType.SAMU,
        latitude=-23.550520,
        longitude=-46.633308,
        speed_kmh=60.0,
        heading_deg=90.0,
        siren_active=True,
    )
    assert telemetry.vehicle_id == "SAMU_01"
    assert telemetry.siren_active is True

    vehicle = EmergencyVehicle(
        vehicle_id="SAMU_01",
        corporation=CorporationType.SAMU,
        latitude=-23.550520,
        longitude=-46.633308,
        speed_kmh=60.0,
        heading_deg=90.0,
        siren_active=True,
    )
    v_dict = vehicle.to_dict()
    assert v_dict["vehicle_id"] == "SAMU_01"
    assert v_dict["corporation"] == "SAMU"
    assert v_dict["siren_active"] is True


@pytest.mark.unit
def test_evp_kinematics_engine():
    """Validates geodetic calculations, block entrance detection, and checkout."""
    kinematics = EVPKinematicsEngine(block_entry_min_meters=60.0, block_entry_max_meters=160.0)

    # 1. Haversine distance between same point must be 0
    dist_zero = kinematics.haversine_distance_meters(-23.550520, -46.633308, -23.550520, -46.633308)
    assert dist_zero == pytest.approx(0.0, abs=1e-3)

    # 2. ~100 meters displacement to the north
    lat_100m = -23.550520 + (100.0 / 111139.0)
    dist_100m = kinematics.haversine_distance_meters(-23.550520, -46.633308, lat_100m, -46.633308)
    assert dist_100m == pytest.approx(100.0, abs=2.0)

    # 3. is_at_block_entrance test (60m - 160m range)
    ref_lat, ref_lon = -23.550520, -46.633308
    lat_100m = ref_lat + (100.0 / 111139.0)
    lat_50m = ref_lat + (50.0 / 111139.0)
    lat_200m = ref_lat + (200.0 / 111139.0)
    assert kinematics.is_at_block_entrance(lat_100m, ref_lon, ref_lat, ref_lon) is True
    assert kinematics.is_at_block_entrance(lat_50m, ref_lon, ref_lat, ref_lon) is False   # Too close (<60m)
    assert kinematics.is_at_block_entrance(lat_200m, ref_lon, ref_lat, ref_lon) is False  # Too far (>160m)

    # 4. has_checked_out test
    lat_10m = ref_lat + (10.0 / 111139.0)
    assert kinematics.has_checked_out(lat_10m, ref_lon, ref_lat, ref_lon, previous_distance=30.0) is True

    # Vehicle moving away after crossing (distance increased from 20m to 35m) -> True
    lat_35m = ref_lat + (35.0 / 111139.0)
    assert kinematics.has_checked_out(lat_35m, ref_lon, ref_lat, ref_lon, previous_distance=20.0) is True


@pytest.mark.unit
def test_evp_kinematics_quadra_length_adaptation():
    """Validates dynamic block adaptation using length provided by map."""
    kinematics = EVPKinematicsEngine()

    ref_lat, ref_lon = -23.550000, -46.630000
    lat_80m = ref_lat + (80.0 / 111139.0)
    lat_150m = ref_lat + (150.0 / 111139.0)
    lat_220m = ref_lat + (220.0 / 111139.0)

    # For a 100m map block:
    # 80m is inside the block
    assert kinematics.is_inside_quadra(lat_80m, ref_lon, ref_lat, ref_lon, quadra_length=100.0) is True
    # 150m is OUTSIDE the block
    assert kinematics.is_inside_quadra(lat_150m, ref_lon, ref_lat, ref_lon, quadra_length=100.0) is False

    # For a 250m map block:
    # 150m and 220m are inside the block
    assert kinematics.is_inside_quadra(lat_150m, ref_lon, ref_lat, ref_lon, quadra_length=250.0) is True
    assert kinematics.is_inside_quadra(lat_220m, ref_lon, ref_lat, ref_lon, quadra_length=250.0) is True

    # Distance test in Cartesian metric coordinates (SUMO)
    dist_sumo = kinematics.calculate_distance_meters(100.0, 500.0, 100.0, 550.0)
    assert dist_sumo == pytest.approx(50.0, abs=1e-3)

