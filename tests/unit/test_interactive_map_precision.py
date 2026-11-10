# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from unittest.mock import MagicMock

import pytest

from ui.components.interactive_map import InteractiveMap


class FakeTapEvent:
    def __init__(self, local_x: float, local_y: float):
        self.local_x = local_x
        self.local_y = local_y


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


def test_interactive_map_traffic_light_border_and_lights_over_street():
    """Validates that clicking on traffic light borders and individual lights (red/yellow/green)
    in the Planning map (InteractiveMap) selects the semaphore and never yields to the street underneath."""
    map_widget = InteractiveMap(project_root="/tmp")
    on_node = MagicMock()
    on_edge = MagicMock()
    map_widget.on_node_click = on_node
    map_widget.on_edge_click = on_edge

    # Semaphore at (100, 100). Icon is 16x42 (half-width=8, half-height=21)
    # Bounds without padding: left=92, right=108, top=79, bottom=121
    # Bounds with 4px padding: left=88, right=112, top=75, bottom=125
    map_widget.drawn_nodes_cache = [{"id": "tl_1", "cx": 100.0, "cy": 100.0, "has_semaphore": True}]
    # Edge passing directly underneath horizontally through (100, 100)
    map_widget.drawn_edges_cache = [
        {"id": "edge_h", "points": [(0.0, 100.0), (300.0, 100.0)], "raw": {}}
    ]

    # 1. Click on Red light at (100, 85) -> 15px from center, 15px from street -> must select semaphore
    map_widget._handle_tap(FakeTapEvent(100.0, 85.0))
    on_node.assert_called_with("tl_1")
    assert map_widget.selected_node_id == "tl_1"
    assert map_widget.selected_edge_id is None

    # Reset selection
    map_widget.set_selected_node(None)

    # 2. Click on Green light at (100, 115) -> 15px from center -> must select semaphore
    map_widget._handle_tap(FakeTapEvent(100.0, 115.0))
    on_node.assert_called_with("tl_1")
    assert map_widget.selected_node_id == "tl_1"

    # Reset selection
    map_widget.set_selected_node(None)

    # 3. Click on left border of semaphore box at (92, 100) right where street passes (dist_street = 0)
    map_widget._handle_tap(FakeTapEvent(92.0, 100.0))
    on_node.assert_called_with("tl_1")
    assert map_widget.selected_node_id == "tl_1"

    # Reset selection
    map_widget.set_selected_node(None)

    # 4. Click on right border of semaphore box at (108, 100) right where street passes (dist_street = 0)
    map_widget._handle_tap(FakeTapEvent(108.0, 100.0))
    on_node.assert_called_with("tl_1")
    assert map_widget.selected_node_id == "tl_1"

    # Reset selection
    map_widget.set_selected_node(None)

    # 5. Click on padding zone at (110, 100) (2px outside box, on street)
    map_widget._handle_tap(FakeTapEvent(110.0, 100.0))
    on_node.assert_called_with("tl_1")
    assert map_widget.selected_node_id == "tl_1"

    # Reset selection
    map_widget.set_selected_node(None)

    # 6. Click beyond padding at (115, 100) (3px outside padding, on street) -> must select street!
    map_widget._handle_tap(FakeTapEvent(115.0, 100.0))
    on_edge.assert_called_with("edge_h", {})
    assert map_widget.selected_edge_id == "edge_h"
    assert map_widget.selected_node_id is None
