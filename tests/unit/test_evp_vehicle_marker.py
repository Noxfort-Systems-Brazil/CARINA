# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Unit tests for emergency vehicle visual marker (EVPVehicleMarker).
Validates scaled dimensions (16x16px), geometries per corporation, and alert color alternation.
"""

from unittest.mock import MagicMock
import flet as ft
import pytest

from ui.widgets.evp_vehicle_marker import EVPVehicleMarker


@pytest.mark.unit
def test_evp_vehicle_marker_dimensions_and_initial_state():
    """Validates that marker has compact width and height (16x16px) proportional to roadway."""
    marker_samu = EVPVehicleMarker(
        vehicle_id="SAMU-01",
        corporation="SAMU",
        initial_lat=-23.55,
        initial_lon=-46.63,
        siren_active=False,
    )
    assert marker_samu.width == 16
    assert marker_samu.height == 16
    assert marker_samu.current_fill_color == "#FFFFFF"

    marker_bomb = EVPVehicleMarker(
        vehicle_id="BOMB-01",
        corporation="BOMBEIROS",
        initial_lat=-23.55,
        initial_lon=-46.63,
        siren_active=False,
    )
    assert marker_bomb.width == 16
    assert marker_bomb.height == 16
    assert marker_bomb.current_fill_color == "#FF9800"

    marker_pm = EVPVehicleMarker(
        vehicle_id="PM-01",
        corporation="POLICIA",
        initial_lat=-23.55,
        initial_lon=-46.63,
        siren_active=False,
    )
    assert marker_pm.width == 16
    assert marker_pm.height == 16
    assert marker_pm.current_fill_color == "#1E3A8A"


@pytest.mark.unit
def test_evp_vehicle_marker_blinking_color_alternation():
    """Validates cyclical color alternation when siren is active."""
    # 1. SAMU (White <-> Bright Red)
    samu = EVPVehicleMarker(
        vehicle_id="SAMU-01",
        corporation="SAMU",
        initial_lat=-23.55,
        initial_lon=-46.63,
        siren_active=True,
    )
    # Alert cycle (True)
    samu.update_state(-23.55, -46.63, 60.0, 90.0, siren_active=True, blink_state=True)
    assert samu.current_fill_color == "#E53935"

    # Rest cycle (False)
    samu.update_state(-23.55, -46.63, 60.0, 90.0, siren_active=True, blink_state=False)
    assert samu.current_fill_color == "#FFFFFF"

    # 2. Firefighters (Orange <-> Fire Red)
    bomb = EVPVehicleMarker(
        vehicle_id="BOMB-01",
        corporation="BOMBEIROS",
        initial_lat=-23.55,
        initial_lon=-46.63,
        siren_active=True,
    )
    bomb.update_state(-23.55, -46.63, 70.0, 180.0, siren_active=True, blink_state=True)
    assert bomb.current_fill_color == "#FF3D00"

    bomb.update_state(-23.55, -46.63, 70.0, 180.0, siren_active=True, blink_state=False)
    assert bomb.current_fill_color == "#FF9800"

    # 3. Police (Dark Blue <-> Electric Blue)
    pm = EVPVehicleMarker(
        vehicle_id="PM-01",
        corporation="POLICIA",
        initial_lat=-23.55,
        initial_lon=-46.63,
        siren_active=True,
    )
    pm.update_state(-23.55, -46.63, 80.0, 270.0, siren_active=True, blink_state=True)
    assert pm.current_fill_color == "#2563EB"

    pm.update_state(-23.55, -46.63, 80.0, 270.0, siren_active=True, blink_state=False)
    assert pm.current_fill_color == "#1E3A8A"


@pytest.mark.unit
def test_evp_vehicle_marker_siren_inactive_stays_base_color():
    """Validates that when siren is off, marker remains in fixed base color."""
    samu = EVPVehicleMarker(
        vehicle_id="SAMU-01",
        corporation="SAMU",
        initial_lat=-23.55,
        initial_lon=-46.63,
        siren_active=False,
    )
    samu.update_state(-23.55, -46.63, 40.0, 90.0, siren_active=False, blink_state=True)
    assert samu.current_fill_color == "#FFFFFF"

    bomb = EVPVehicleMarker(
        vehicle_id="BOMB-01",
        corporation="BOMBEIROS",
        initial_lat=-23.55,
        initial_lon=-46.63,
        siren_active=False,
    )
    bomb.update_state(-23.55, -46.63, 40.0, 90.0, siren_active=False, blink_state=True)
    assert bomb.current_fill_color == "#FF9800"


@pytest.mark.unit
def test_evp_vehicle_marker_safe_page_update_when_mounted():
    """Validates that update is safely invoked when control is mounted on Flet page."""
    marker = EVPVehicleMarker(
        vehicle_id="SAMU-01",
        corporation="SAMU",
        initial_lat=-23.55,
        initial_lon=-46.63,
        siren_active=True,
    )
    mock_page = MagicMock(spec=ft.Page)
    marker._Control__page = mock_page
    marker.shape_canvas._Control__page = mock_page

    with MagicMock() as mock_update:
        marker.shape_canvas.update = mock_update
        marker.update_state(-23.55, -46.63, 50.0, 90.0, siren_active=True, blink_state=True)
        assert mock_update.called


@pytest.mark.unit
def test_evp_vehicle_marker_preserves_canvas_instance_in_place():
    """Validates that Canvas instance is not recreated upon update (avoids AssertionError in Flet)."""
    marker = EVPVehicleMarker(
        vehicle_id="SAMU-01",
        corporation="SAMU",
        initial_lat=-23.55,
        initial_lon=-46.63,
        siren_active=True,
    )
    original_canvas = marker.content
    marker.update_state(-23.55, -46.63, 60.0, 90.0, siren_active=True, blink_state=True)
    assert marker.content is original_canvas
    assert marker.fill_paint.color == "#E53935"

    marker.update_state(-23.55, -46.63, 60.0, 90.0, siren_active=True, blink_state=False)
    assert marker.content is original_canvas
    assert marker.fill_paint.color == "#FFFFFF"


@pytest.mark.unit
def test_evp_vehicle_marker_blinks_on_evp_preemption_triggered():
    """Validates that marker blinks when is_evp_triggered=True, even if siren_active=False."""
    marker = EVPVehicleMarker(
        vehicle_id="PM-01",
        corporation="POLICIA",
        initial_lat=-23.55,
        initial_lon=-46.63,
        siren_active=False,
        is_evp_triggered=True,
    )
    # Alert cycle (True)
    marker.update_state(-23.55, -46.63, 50.0, 90.0, siren_active=False, blink_state=True, is_evp_triggered=True)
    assert marker.current_fill_color == "#2563EB"
    assert marker.fill_paint.color == "#2563EB"

    # Rest cycle (False)
    marker.update_state(-23.55, -46.63, 50.0, 90.0, siren_active=False, blink_state=False, is_evp_triggered=True)
    assert marker.current_fill_color == "#1E3A8A"
    assert marker.fill_paint.color == "#1E3A8A"

