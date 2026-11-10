# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import math

import flet.canvas as cv
import pytest

from ui.renderers.planning_map_renderer import PlanningMapRenderer


def test_planning_map_renderer_hit_radius():
    """Validates that PlanningMapRenderer has reduced hit radius to prevent swallowing streets."""
    renderer = PlanningMapRenderer(1200, 800)
    assert renderer.hit_radius == 14.0


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
