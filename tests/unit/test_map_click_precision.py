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

# File: tests/unit/test_map_click_precision.py
# Author: Gabriel Moraes
# Date: September 2026

import math
from unittest.mock import MagicMock

import flet as ft
import flet.canvas as cv
import pytest

from ui.components.interactive_map import InteractiveMap
from ui.handlers.map_interaction_handler import MapInteractionHandler
from ui.handlers.street_interaction_handler import StreetInteractionHandler
from ui.managers.map_state_manager import MapStateManager
from ui.renderers.planning_map_renderer import PlanningMapRenderer
from ui.router.map_event_router import MapEventRouter


class FakeScrollEvent:
    def __init__(self, delta_y: float, local_x: float = None, local_y: float = None):
        self.scroll_delta_y = delta_y
        self.local_x = local_x
        self.local_y = local_y


class FakeTapEvent:
    def __init__(self, local_x: float, local_y: float):
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


def test_event_router_disambiguation_traffic_light_vs_street():
    """Validates smart disambiguation between traffic lights and street lines."""
    interaction_handler = MapInteractionHandler(800.0, 600.0, on_update_callback=MagicMock())
    street_handler = StreetInteractionHandler(on_street_selected=MagicMock())

    on_tl_clicked = MagicMock()
    on_st_clicked = MagicMock()

    router = MapEventRouter(
        interaction_handler=interaction_handler,
        street_interaction_handler=street_handler,
        safe_update_callback=MagicMock(),
        on_semaphore_click=on_tl_clicked,
        on_street_click=on_st_clicked,
    )
    street_handler.on_street_selected = router.handle_street_click

    # Mock a traffic light at (100, 100), width=20, height=50 (left=90, top=75)
    mock_tl = ft.Container(width=20, height=50, left=90, top=75)
    interactive_widgets = {"tl_1": mock_tl}

    # Road going horizontally through the intersection: from (100, 100) to (300, 100)
    road_path = cv.Path([cv.Path.MoveTo(100, 100), cv.Path.LineTo(300, 100)])
    street_handler.load_paths({"edge_h": road_path})

    state_manager = MapStateManager(
        canvas=MagicMock(spec=cv.Canvas, shapes=[]),
        stack=MagicMock(spec=ft.Stack, controls=[]),
        edge_paths={"edge_h": road_path},
        interactive_widgets=interactive_widgets,
    )
    router.attach_managers(state_manager=state_manager, animator=None)

    # Test 1: Click directly on traffic light center (100, 100)
    router.handle_map_tap(FakeTapEvent(100.0, 100.0))
    on_tl_clicked.assert_called_with("tl_1")
    assert state_manager.selected_interactive_id == "tl_1"
    assert state_manager.selected_edge_id is None

    # Test 2: Click along the road at (130, 101) - clearly on road
    router.handle_map_tap(FakeTapEvent(130.0, 101.0))
    on_st_clicked.assert_called_with("edge_h")
    assert state_manager.selected_edge_id == "edge_h"
    assert state_manager.selected_interactive_id is None

    # Test 3: Click again on road to toggle off
    router.handle_map_tap(FakeTapEvent(115.0, 100.0))
    on_st_clicked.assert_called_with(None)
    assert state_manager.selected_edge_id is None

    # Test 4: Click on empty background (400, 400)
    router.handle_map_tap(FakeTapEvent(400.0, 400.0))
    assert state_manager.selected_edge_id is None
    assert state_manager.selected_interactive_id is None


def test_planning_map_renderer_hit_radius():
    """Validates that PlanningMapRenderer has reduced hit radius to prevent swallowing streets."""
    renderer = PlanningMapRenderer(1200, 800)
    assert renderer.hit_radius == 14.0


def test_interactive_map_disambiguation():
    """Validates that InteractiveMap disambiguates nodes and edges properly."""
    map_widget = InteractiveMap(project_root="/tmp")
    on_node = MagicMock()
    on_edge = MagicMock()
    map_widget.on_node_click = on_node
    map_widget.on_edge_click = on_edge

    # Junction node at (100, 100)
    map_widget.drawn_nodes_cache = [{"id": "node_1", "cx": 100.0, "cy": 100.0}]
    # Edge from (100, 100) to (300, 100)
    map_widget.drawn_edges_cache = [{"id": "edge_1", "points": [(100.0, 100.0), (300.0, 100.0)], "raw": {}}]

    # Click at (102, 100) -> 2px from node, 0px from edge -> min_node_dist (2) < min_edge_dist (0) + 2.0 -> Node
    map_widget._handle_tap(FakeTapEvent(102.0, 100.0))
    on_node.assert_called_with("node_1")
    assert map_widget.selected_node_id == "node_1"
    assert map_widget.selected_edge_id is None

    # Click along the street at (115, 100) -> 15px from node, 0px from edge -> Edge selected!
    map_widget._handle_tap(FakeTapEvent(115.0, 100.0))
    on_edge.assert_called_with("edge_1", {})
    assert map_widget.selected_edge_id == "edge_1"
    assert map_widget.selected_node_id is None


def test_planning_map_layer_synchronization_on_resize():
    """Validates that canvas_static (streets) and canvas_dynamic (nodes/semaphores) stay 100% in sync on resize."""
    renderer = PlanningMapRenderer(base_width=1200, base_height=800)
    topology = {
        "bounds": {"min_x": 0, "max_x": 100, "min_y": 0, "max_y": 100},
        "nodes": {
            "n1": {"id": "n1", "x": 50, "y": 50, "type": "traffic_light"},
            "n2": {"id": "n2", "x": 80, "y": 50, "type": "priority"},
        },
        "edges": [
            {"id": "e1", "from": "n1", "to": "n2", "shape": [[50, 50], [80, 50]]},
        ],
    }

    renderer.calculate_initial_fit(topology)
    canvas_static = cv.Canvas(shapes=[])
    canvas_dynamic = cv.Canvas(shapes=[])
    drawn_nodes_cache = []
    drawn_edges_cache = []

    # First draw at 1200x800
    renderer.draw_topology(
        topology=topology,
        canvas_static=canvas_static,
        canvas_dynamic=canvas_dynamic,
        drawn_nodes_cache=drawn_nodes_cache,
        drawn_edges_cache=drawn_edges_cache,
    )

    # Initial check: node center and street start point must match exactly
    node_circle = [s for s in canvas_dynamic.shapes if isinstance(s, cv.Circle)][0]
    street_path = canvas_static.shapes[0]
    first_pt = street_path.elements[0]  # MoveTo
    assert math.isclose(node_circle.x, first_pt.x, abs_tol=1e-3)
    assert math.isclose(node_circle.y, first_pt.y, abs_tol=1e-3)

    # Resize to 1600x900 (as on larger or smaller desktop display)
    renderer.base_width = 1600
    renderer.base_height = 900
    renderer.calculate_initial_fit(topology)

    # Redraw topology
    renderer.draw_topology(
        topology=topology,
        canvas_static=canvas_static,
        canvas_dynamic=canvas_dynamic,
        drawn_nodes_cache=drawn_nodes_cache,
        drawn_edges_cache=drawn_edges_cache,
    )

    # After redraw, static streets must have been updated to new coordinates, NOT frozen at old coordinates!
    new_node_circle = [s for s in canvas_dynamic.shapes if isinstance(s, cv.Circle)][0]
    new_street_path = canvas_static.shapes[0]
    new_first_pt = new_street_path.elements[0]

    # Node moved because width changed
    assert not math.isclose(node_circle.x, new_node_circle.x, abs_tol=1.0)
    # AND street must match the new node position with 0.00 drift!
    assert math.isclose(new_node_circle.x, new_first_pt.x, abs_tol=1e-3)
    assert math.isclose(new_node_circle.y, new_first_pt.y, abs_tol=1e-3)
