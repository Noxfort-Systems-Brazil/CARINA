# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import math
from unittest.mock import MagicMock

import flet.canvas as cv
import pytest

from ui.handlers.map_interaction_handler import MapInteractionHandler
from ui.handlers.street_interaction_handler import StreetInteractionHandler


class FakeScrollEvent:
    def __init__(self, delta_y: float, local_x: float = None, local_y: float = None):
        self.scroll_delta_y = delta_y
        self.local_x = local_x
        self.local_y = local_y


def test_zoom_pointer_anchoring_zero_drift():
    """Validates that zooming in and out maintains exact 0.000000 drift under the mouse pointer."""
    handler = MapInteractionHandler(800.0, 600.0, on_update_callback=MagicMock())
    cursor_x, cursor_y = 550.0, 420.0

    orig_map_x, orig_map_y = handler.get_map_coordinates(cursor_x, cursor_y)

    # 1. Zoom in 10 steps
    for _ in range(10):
        evt = FakeScrollEvent(delta_y=-100, local_x=cursor_x, local_y=cursor_y)
        handler.handle_zoom(evt)
        curr_map_x, curr_map_y = handler.get_map_coordinates(cursor_x, cursor_y)
        assert math.isclose(curr_map_x, orig_map_x, abs_tol=1e-5)
        assert math.isclose(curr_map_y, orig_map_y, abs_tol=1e-5)

    assert handler.scale.scale > 2.0

    # 2. Zoom out 10 steps back
    for _ in range(10):
        evt = FakeScrollEvent(delta_y=100, local_x=cursor_x, local_y=cursor_y)
        handler.handle_zoom(evt)
        curr_map_x, curr_map_y = handler.get_map_coordinates(cursor_x, cursor_y)
        assert math.isclose(curr_map_x, orig_map_x, abs_tol=1e-5)
        assert math.isclose(curr_map_y, orig_map_y, abs_tol=1e-5)


def test_scroll_event_extracts_local_coords():
    """Validates that handle_zoom extracts coordinates directly from ScrollEvent."""
    handler = MapInteractionHandler(800.0, 600.0, on_update_callback=MagicMock())
    cursor_x, cursor_y = 300.0, 200.0

    evt = FakeScrollEvent(delta_y=-100, local_x=cursor_x, local_y=cursor_y)
    # Pass dummy mouse_x, mouse_y to ensure event local_x/local_y takes precedence
    handler.handle_zoom(evt, mouse_x=999.0, mouse_y=999.0)

    # Map point under (300, 200) should be preserved
    expected_map_x = ((300.0 - 400.0) / 1.0) + 400.0 - 0.0
    actual_map_x, _ = handler.get_map_coordinates(300.0, 200.0)
    assert math.isclose(actual_map_x, expected_map_x, abs_tol=1e-5)


def test_street_interaction_handler_tolerance_and_caching():
    """Validates that StreetInteractionHandler caches points and uses 25px threshold."""
    selected_edges = []
    handler = StreetInteractionHandler(on_street_selected=lambda eid: selected_edges.append(eid))
    assert handler.base_hit_threshold == 25.0

    # Create dummy path for edge_1 from (100, 100) to (300, 100)
    path = cv.Path([cv.Path.MoveTo(100, 100), cv.Path.LineTo(300, 100)])
    handler.load_paths({"edge_1": path})

    assert "edge_1" in handler.edge_points
    assert handler.edge_points["edge_1"] == [(100, 100), (300, 100)]

    # 1. Click directly on edge
    closest_id, dist = handler.find_closest_edge(200.0, 100.0)
    assert closest_id == "edge_1"
    assert dist == 0.0

    # 2. Click 20px away (within 25px threshold)
    handler.handle_click(200.0, 120.0, current_scale=1.0)
    assert selected_edges[-1] == "edge_1"

    # 3. Click again to toggle unselect
    handler.handle_click(200.0, 120.0, current_scale=1.0)
    assert selected_edges[-1] is None

    # 4. Click 30px away (beyond 25px threshold)
    handler.handle_click(200.0, 130.0, current_scale=1.0)
    assert selected_edges[-1] is None


class FakeDragEvent:
    def __init__(self, delta_x: float, delta_y: float):
        self.delta_x = delta_x
        self.delta_y = delta_y


def test_zoom_pointer_anchoring_with_non_zero_pan_offset():
    """Validates that zooming preserves cursor point even when map has been panned."""
    handler = MapInteractionHandler(800.0, 600.0, on_update_callback=MagicMock())
    handler.offset.x = 0.15
    handler.offset.y = -0.22
    cursor_x, cursor_y = 520.0, 380.0

    orig_map_x, orig_map_y = handler.get_map_coordinates(cursor_x, cursor_y)

    # Zoom in 8 steps
    for _ in range(8):
        evt = FakeScrollEvent(delta_y=-100, local_x=cursor_x, local_y=cursor_y)
        handler.handle_zoom(evt)
        curr_map_x, curr_map_y = handler.get_map_coordinates(cursor_x, cursor_y)
        assert math.isclose(curr_map_x, orig_map_x, abs_tol=1e-5)
        assert math.isclose(curr_map_y, orig_map_y, abs_tol=1e-5)

    # Zoom out 8 steps
    for _ in range(8):
        evt = FakeScrollEvent(delta_y=100, local_x=cursor_x, local_y=cursor_y)
        handler.handle_zoom(evt)
        curr_map_x, curr_map_y = handler.get_map_coordinates(cursor_x, cursor_y)
        assert math.isclose(curr_map_x, orig_map_x, abs_tol=1e-5)
        assert math.isclose(curr_map_y, orig_map_y, abs_tol=1e-5)


@pytest.mark.parametrize("scale_val", [0.5, 0.8, 1.0, 1.5, 2.5])
@pytest.mark.parametrize("off_x, off_y", [(0.0, 0.0), (0.1, -0.15), (-0.25, 0.3)])
def test_round_trip_screen_to_map_transformation(scale_val, off_x, off_y):
    """Validates exact algebraic invertibility between screen space and map space."""
    W, H = 1000.0, 800.0
    handler = MapInteractionHandler(W, H, on_update_callback=MagicMock())
    handler.scale.scale = scale_val
    handler.offset.x = off_x
    handler.offset.y = off_y

    test_map_x, test_map_y = 350.0, 520.0
    cx, cy = W / 2.0, H / 2.0
    # Forward Flutter transform:
    screen_x = (test_map_x - cx) * scale_val + cx + (off_x * W)
    screen_y = (test_map_y - cy) * scale_val + cy + (off_y * H)

    computed_map_x, computed_map_y = handler.get_map_coordinates(screen_x, screen_y)
    assert math.isclose(computed_map_x, test_map_x, abs_tol=1e-6)
    assert math.isclose(computed_map_y, test_map_y, abs_tol=1e-6)


def test_pan_tracking_1_to_1_under_different_zoom_levels():
    """Validates that panning moves the canvas 1:1 on screen regardless of scale."""
    W, H = 800.0, 600.0
    handler = MapInteractionHandler(W, H, on_update_callback=MagicMock())

    for zoom in [0.5, 1.0, 2.0]:
        handler.scale.scale = zoom
        handler.offset.x = 0.0
        handler.offset.y = 0.0

        drag_evt = FakeDragEvent(delta_x=50.0, delta_y=30.0)
        handler.handle_pan_update(drag_evt)

        # Expected shift in screen pixels is exactly delta_x, delta_y
        screen_shift_x = handler.offset.x * W
        screen_shift_y = handler.offset.y * H
        assert math.isclose(screen_shift_x, 50.0, abs_tol=1e-6)
        assert math.isclose(screen_shift_y, 30.0, abs_tol=1e-6)

