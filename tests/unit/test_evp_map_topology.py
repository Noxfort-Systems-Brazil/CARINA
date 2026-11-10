# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from src.evp.evp_models import CorporationType, RegisteredVehicle, TelemetryData
from src.evp.evp_service import EVPService


@pytest.mark.unit
def test_evp_automatic_map_topology_ingestion():
    """Validates automatic road network vector ingestion and block mapping."""
    service = EVPService()
    map_data = (
        {
            "INT_A": {"id": "INT_A", "x": -46.633, "y": -23.550, "type": "traffic_light"},
            "INT_B": {"id": "INT_B", "x": -46.630, "y": -23.550, "type": "traffic_light"},
            "NODE_C": {"id": "NODE_C", "x": -46.635, "y": -23.550, "type": "priority"},
        },
        [
            {"id": "edge_C_A", "from": "NODE_C", "to": "INT_A", "length": 95.0, "name": "Rua das Flores"},
            {"id": "edge_A_B", "from": "INT_A", "to": "INT_B", "length": 210.0, "name": "Av. Principal"},
        ],
        {},
    )

    count = service.load_map_data(map_data)
    assert count == 2
    assert "INT_A" in service._intersections_geo
    assert "INT_B" in service._intersections_geo
    assert "INT_A" in service._intersection_quadras
    assert service._intersection_quadras["INT_A"][0]["length"] == 95.0
    assert service._intersection_quadras["INT_B"][0]["length"] == 210.0


@pytest.mark.unit
def test_evp_auto_trigger_on_quadra_entry_with_map():
    """Validates that EVP automatically triggers upon entering map block in alert mode."""
    dispatched = []

    def mock_dispatch(int_id, action, reason):
        dispatched.append((int_id, action, reason))

    service = EVPService(on_action_dispatch=mock_dispatch)
    service.register_fleet_vehicle(
        RegisteredVehicle(vehicle_id="RESGATE_01", corporation=CorporationType.BOMBEIROS)
    )

    int_lat, int_lon = -23.550000, -46.630000
    map_data = (
        {"INT_MAP": {"id": "INT_MAP", "x": int_lon, "y": int_lat, "type": "traffic_light"}},
        [{"id": "quadra_01", "from": "N_ORIG", "to": "INT_MAP", "length": 140.0}],
        {},
    )
    service.load_map_data(map_data)

    # 1. Far from block (180m > 140m): Even with siren on, does NOT activate
    lat_180m = int_lat + (180.0 / 111139.0)
    t_fora = TelemetryData(
        vehicle_id="RESGATE_01",
        corporation=CorporationType.BOMBEIROS,
        latitude=lat_180m,
        longitude=int_lon,
        siren_active=True,
    )
    service.process_telemetry(t_fora)
    assert service.is_preemption_active("INT_MAP") is False

    # 2. Entering block (100m <= 140m) with siren on (Alert Mode): ACTIVATES AUTOMATICALLY!
    lat_100m = int_lat + (100.0 / 111139.0)
    t_dentro = TelemetryData(
        vehicle_id="RESGATE_01",
        corporation=CorporationType.BOMBEIROS,
        latitude=lat_100m,
        longitude=int_lon,
        siren_active=True,
    )
    service.process_telemetry(t_dentro)
    assert service.is_preemption_active("INT_MAP") is True
    assert any(d[0] == "INT_MAP" and d[2] == "ACTIVATE_PREEMPT" for d in dispatched)

    # 3. Vehicle crosses intersection (Checkout at 10m): DEACTIVATES AUTOMATICALLY!
    lat_10m = int_lat + (10.0 / 111139.0)
    t_checkout = TelemetryData(
        vehicle_id="RESGATE_01",
        corporation=CorporationType.BOMBEIROS,
        latitude=lat_10m,
        longitude=int_lon,
        siren_active=True,
    )
    service.process_telemetry(t_checkout)
    assert service.is_preemption_active("INT_MAP") is False


@pytest.mark.unit
def test_ui_settings_no_manual_evp_parameters():
    """Ensures system settings UI no longer includes manual block parameter fields."""
    import ui.builders.settings_configurator as cfg_mod

    assert not hasattr(cfg_mod, "EVPSafetyParametersCard")


@pytest.mark.unit
def test_evp_topology_geodetic_conversion():
    """Validates bidirectional conversion between SUMO metric coordinates and GPS WGS84."""
    from src.evp.evp_topology_service import EVPTopologyService
    from src.utils.sumo_geo_bounds_reader import SumoGeoBounds

    topo = EVPTopologyService()
    bounds = SumoGeoBounds(
        min_lon=-51.240163,
        min_lat=-23.515986,
        max_lon=-51.233151,
        max_lat=-23.507576,
        min_x=0.0,
        min_y=0.0,
        max_x=715.96,
        max_y=930.36,
        proj_parameter="+proj=utm +zone=22 +ellps=WGS84 +datum=WGS84 +units=m +no_defs",
        net_offset=(-475481.54, 2600660.66),
    )
    topo.set_geo_bounds(bounds)

    # Conversion of SAMU-01 GPS -> SUMO
    lat, lon = -23.5124, -51.2361
    sumo_x, sumo_y = topo.lat_lon_to_sumo(lat, lon)
    assert 400.0 < sumo_x < 430.0
    assert 380.0 < sumo_y < 410.0

    # Inverse conversion SUMO -> GPS
    rev_lat, rev_lon = topo.sumo_to_lat_lon(sumo_x, sumo_y)
    assert pytest.approx(rev_lat, abs=1e-4) == lat
    assert pytest.approx(rev_lon, abs=1e-4) == lon


@pytest.mark.unit
def test_evp_overlay_manager_geodetic_projection():
    """Validates vehicle projection on canvas via EVPOverlayManager with geodetic topology."""
    from unittest.mock import MagicMock
    from src.evp.evp_service import EVPService
    from src.utils.sumo_geo_bounds_reader import SumoGeoBounds
    from ui.managers.evp_overlay_manager import EVPOverlayManager

    service = EVPService.get_instance()
    bounds = SumoGeoBounds(
        min_lon=-51.240163,
        min_lat=-23.515986,
        max_lon=-51.233151,
        max_lat=-23.507576,
        min_x=0.0,
        min_y=0.0,
        max_x=715.96,
        max_y=930.36,
        proj_parameter="+proj=utm +zone=22 +ellps=WGS84 +datum=WGS84 +units=m +no_defs",
        net_offset=(-475481.54, 2600660.66),
    )
    service.topology_service.set_geo_bounds(bounds)

    mock_drawer = MagicMock()
    mock_drawer.nodes = {"INT_1": {"x": 311.94, "y": 854.79}}
    mock_drawer.sumo_center_x = 357.98
    mock_drawer.sumo_center_y = 465.18
    mock_drawer.transform_point.side_effect = lambda sx, sy: (600.0 + (sx - 357.98), 400.0 - (sy - 465.18))

    mgr = EVPOverlayManager(
        map_stack=MagicMock(),
        get_drawer=lambda: mock_drawer,
        get_viewport_manager=lambda: MagicMock(width=1200.0, height=800.0),
        get_animator=lambda: MagicMock(blink_toggle=False),
    )

    cx, cy = mgr.project_vehicle_to_canvas(-23.5124, -51.2361)
    # Must be within visible Canvas boundaries (not 20 million pixels)
    assert 500.0 < cx < 800.0
    assert 300.0 < cy < 600.0
