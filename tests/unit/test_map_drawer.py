# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from unittest.mock import MagicMock

import flet.canvas as cv
import pytest

from ui.animators.map_animator import MapAnimator
from ui.renderers.map_drawer import MapDrawer


@pytest.fixture
def sample_map_data():
    nodes = {
        "node_1": {"x": 0.0, "y": 0.0, "type": "traffic_light"},
        "node_2": {"x": 100.0, "y": 0.0, "type": "priority"},
        "node_3": {"x": 100.0, "y": 100.0, "type": "priority"},
    }
    edges = [
        {"id": "edge_1_2", "from": "node_1", "to": "node_2", "shape": [[0.0, 0.0], [100.0, 0.0]]},
        {"id": "edge_2_3", "from": "node_2", "to": "node_3", "shape": [[100.0, 0.0], [100.0, 100.0]]},
    ]
    return (nodes, edges, {})


def test_map_drawer_with_initial_congestion(sample_map_data):
    nodes, edges, _ = sample_map_data
    drawer = MapDrawer(nodes, edges)
    drawer.calculate_transformations(800, 600)

    canvas = cv.Canvas(shapes=[], width=800, height=600)
    initial_congestion = {"edge_1_2": 95.0, "edge_2_3": 0.0}

    edge_paths = drawer.draw_initial_map(canvas, stroke_width=7.0, initial_congestion=initial_congestion)

    assert edge_paths["edge_1_2"].paint.color != "#2ecc71"
    assert edge_paths["edge_2_3"].paint.color == "#2ecc71"


def test_map_animator_initial_data():
    mock_widget = MagicMock()
    initial_congestion = {"edge_1": 80.0}
    initial_panel = {"tl_1": {"phase": "RED"}}
    initial_street_overrides = {"edge_2": "BLOCKED"}
    initial_semaphore_overrides = {"tl_1": "ALERT"}

    animator = MapAnimator(
        widget_to_update=mock_widget,
        initial_congestion_data=initial_congestion,
        initial_panel_data=initial_panel,
        initial_street_overrides=initial_street_overrides,
        initial_semaphore_overrides=initial_semaphore_overrides,
    )

    assert animator.latest_congestion_data == {"edge_1": 80.0}
    assert animator.latest_panel_data == {"tl_1": {"phase": "RED"}}
    assert animator.override_manager.get_street_overrides() == {"edge_2": "BLOCKED"}
    assert animator.override_manager.get_semaphore_overrides() == {"tl_1": "ALERT"}


def test_map_animator_safe_partial_update():
    mock_widget = MagicMock()
    animator = MapAnimator(
        widget_to_update=mock_widget,
        initial_congestion_data={"edge_1": 50.0},
        initial_panel_data={"tl_1": {"state": "active"}},
    )

    animator.update_data({"type": "fast_update", "panel_data": {"tl_1": {"state": "updated"}}})
    assert animator.latest_congestion_data == {"edge_1": 50.0}
    assert animator.latest_panel_data == {"tl_1": {"state": "updated"}}

    animator.update_data({"type": "congestion_update", "payload": {"edge_2": 90.0}})
    assert animator.latest_congestion_data["edge_1"] == 50.0
    assert animator.latest_congestion_data["edge_2"] == 90.0
    assert animator.latest_panel_data == {"tl_1": {"state": "updated"}}


def test_map_drawer_dead_ends_do_not_extend_or_draw_points():
    """Validates that dead-end streets terminate cleanly at the end of their geometry
    without extending to node center offsets, and that no circles/points are drawn at dead ends."""
    import math

    nodes = {
        "j_main": {"x": 50.0, "y": 50.0, "type": "traffic_light"},
        "j_dead": {"x": 100.0, "y": 55.0, "type": "dead_end"},
    }
    edges = [
        {"id": "e_dead", "from": "j_main", "to": "j_dead", "shape": [[50.0, 50.0], [90.0, 50.0]]}
    ]
    drawer = MapDrawer(nodes, edges)
    drawer.calculate_transformations(800, 600)

    canvas = cv.Canvas(shapes=[], width=800, height=600)
    edge_paths = drawer.draw_initial_map(canvas, stroke_width=5.0)

    path = edge_paths["e_dead"]
    # Path should end at (90, 50), and NOT extend to j_dead at (100, 55)
    last_element = path.elements[-1]
    expected_x, expected_y = drawer.transform_point(90.0, 50.0)
    dead_node_x, dead_node_y = drawer.transform_point(100.0, 55.0)

    assert math.isclose(last_element.x, expected_x, abs_tol=1e-3)
    assert math.isclose(last_element.y, expected_y, abs_tol=1e-3)
    assert not math.isclose(last_element.x, dead_node_x, abs_tol=1.0)

    # Ensure no cv.Circle is drawn on canvas for dead end
    circles = [s for s in canvas.shapes if isinstance(s, cv.Circle)]
    assert len(circles) == 0
