# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: tests/unit/test_map_drawer.py
# Author: Gabriel Moraes
# Date: September 2026

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
