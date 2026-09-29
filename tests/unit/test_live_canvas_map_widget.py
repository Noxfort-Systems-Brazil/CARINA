# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: tests/unit/test_live_canvas_map_widget.py
# Author: Gabriel Moraes
# Date: September 2026

from unittest.mock import MagicMock, patch

import flet as ft
import flet.canvas as cv
import pytest

from ui.animators.map_animator import MapAnimator
from ui.builders.map_scene_builder import MapSceneBuilder
from ui.handlers.locale_manager import LocaleManager
from ui.managers.map_state_manager import MapStateManager
from ui.managers.map_telemetry_manager import MapTelemetryManager
from ui.renderers.map_visual_syncer import MapVisualSyncer
from ui.widgets.live_canvas_map_widget import LiveCanvasMapWidget


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


def test_live_canvas_map_widget_data_persistence_on_rebuild(sample_map_data):
    mock_lm = MagicMock(spec=LocaleManager)
    mock_lm.get_string.side_effect = lambda key, default=None, **kwargs: default or key

    map_widget = LiveCanvasMapWidget(locale_manager=mock_lm)
    mock_page = MagicMock(spec=ft.Page)
    mock_page.width = 1280
    mock_page.height = 800
    map_widget._Control__page = mock_page

    map_widget.initialize_map(sample_map_data)

    map_widget.update_data(
        {
            "type": "congestion_update",
            "payload": {"edge_1_2": 95.0, "edge_2_3": 50.0},
            "panel_data": {"node_1": {"brand": "Swarco", "state": "active"}},
        }
    )

    assert map_widget._latest_congestion_data["edge_1_2"] == 95.0
    assert map_widget._latest_panel_data["node_1"]["brand"] == "Swarco"

    assert map_widget.map_state_manager is not None
    map_widget.map_state_manager.set_selection(item_type="street", item_id="edge_1_2")

    map_widget.set_street_override_state("edge_2_3", "BLOCKED")
    if map_widget.animator:
        map_widget.animator.override_manager.process_queue()

    map_widget.viewport_manager.width = 1600
    map_widget.viewport_manager.height = 900
    map_widget._build_map(sample_map_data)

    assert map_widget.animator.edge_paths["edge_1_2"].paint.color != "#2ecc71"
    assert map_widget.animator.edge_paths["edge_2_3"].paint.color == "#000000"
    assert map_widget.map_state_manager.selected_edge_id == "edge_1_2"
    assert map_widget.animator.override_manager.get_street_overrides() == {"edge_2_3": "BLOCKED"}

    map_widget.on_unmount()


def test_live_canvas_map_widget_resize_handler_filters_bogus_events(sample_map_data):
    mock_lm = MagicMock(spec=LocaleManager)
    mock_lm.get_string.side_effect = lambda key, default=None, **kwargs: default or key

    map_widget = LiveCanvasMapWidget(locale_manager=mock_lm)
    mock_page = MagicMock(spec=ft.Page)
    mock_page.width = 1280
    mock_page.height = 800
    mock_page.on_resized = None

    map_widget._Control__page = mock_page
    map_widget.initialize_map(sample_map_data)
    map_widget._on_mount()

    assert mock_page.on_resized is not None
    resize_cb = mock_page.on_resized

    with patch.object(map_widget, "_build_map") as mock_build:
        mock_page.width = 1280
        mock_page.height = 800
        resize_cb(MagicMock())
        assert not mock_build.called

        mock_page.width = 0
        mock_page.height = 0
        resize_cb(MagicMock())
        assert not mock_build.called

        mock_page.width = 1920
        mock_page.height = 1080
        resize_cb(MagicMock())
        assert mock_build.called

    map_widget.on_unmount()


def test_map_telemetry_manager():
    tm = MapTelemetryManager()

    tm.update_from_packet(
        {
            "type": "initial_map_geometry",
            "congestion_update": {"edge_1": 25.0},
            "panel_data": {"tl_1": {"phase": "RED"}},
            "street_data": {"edge_1": {"speed": 40}},
        }
    )
    assert tm.get_congestion_data() == {"edge_1": 25.0}
    assert tm.get_panel_data() == {"tl_1": {"phase": "RED"}}
    assert tm.get_street_data() == {"edge_1": {"speed": 40}}

    tm.update_from_packet({"type": "congestion_update", "payload": {"edge_2": 75.0}})
    assert tm.get_congestion_data() == {"edge_1": 25.0, "edge_2": 75.0}
    assert tm.get_panel_data() == {"tl_1": {"phase": "RED"}}

    tm.merge_congestion_data({"edge_3": 10.0})
    assert tm.get_congestion_data()["edge_3"] == 10.0
    tm.clear()
    assert tm.get_congestion_data() == {}
    assert tm.get_panel_data() == {}
    assert tm.get_street_data() == {}


def test_map_visual_syncer():
    syncer = MapVisualSyncer()

    path_mock = MagicMock(spec=cv.Path)
    path_mock.paint = ft.Paint(
        stroke_width=5.0, color="#2ecc71", style=ft.PaintingStyle.STROKE, stroke_cap=ft.StrokeCap.ROUND
    )
    edge_paths = {"edge_1": path_mock}

    widget_mock = MagicMock()
    interactive_widgets = {"tl_1": widget_mock}
    topology_edges = [{"id": "edge_1", "from": "n1", "to": "n2"}]

    syncer.sync_cached_visuals(
        edge_paths=edge_paths,
        interactive_widgets_map=interactive_widgets,
        topology_edges=topology_edges,
        congestion_data={"edge_1": 90.0},
        street_overrides={},
        semaphore_overrides={},
        panel_data={"tl_1": {"state": "active"}},
    )
    assert path_mock.paint.color != "#2ecc71"
    widget_mock.apply_telemetry.assert_called_once()

    syncer.sync_cached_visuals(
        edge_paths=edge_paths,
        interactive_widgets_map=interactive_widgets,
        topology_edges=topology_edges,
        congestion_data={"edge_1": 90.0},
        street_overrides={"edge_1": "BLOCKED"},
        semaphore_overrides={},
        panel_data={},
    )
    assert path_mock.paint.color == "#000000"


def test_map_state_manager_and_animator_queries():
    state_mgr = MapStateManager(
        canvas=MagicMock(spec=cv.Canvas, shapes=[]),
        stack=MagicMock(spec=ft.Stack, controls=[]),
        edge_paths={},
        interactive_widgets={},
    )
    assert state_mgr.get_selected_type_and_id() == (None, None)
    state_mgr.selected_edge_id = "edge_abc"
    assert state_mgr.get_selected_type_and_id() == ("street", "edge_abc")
    state_mgr.selected_edge_id = None
    state_mgr.selected_interactive_id = "tl_xyz"
    assert state_mgr.get_selected_type_and_id() == ("interactive", "tl_xyz")

    animator = MapAnimator(
        widget_to_update=MagicMock(),
        initial_street_overrides={"edge_1": "BLOCKED"},
        initial_semaphore_overrides={"tl_1": "ALERT"},
    )
    streets, semaphores = animator.get_active_overrides()
    assert streets == {"edge_1": "BLOCKED"}
    assert semaphores == {"tl_1": "ALERT"}


def test_map_scene_builder(sample_map_data):
    builder = MapSceneBuilder()

    mock_stack = ft.Stack()
    mock_widget = MagicMock()
    mock_telemetry = MapTelemetryManager()
    mock_telemetry.update_from_packet({"type": "congestion_update", "payload": {"edge_1_2": 85.0}})
    mock_syncer = MapVisualSyncer()

    from ui.builders.map_components_factory import MapComponentsFactory
    from ui.builders.map_controls_assembler import MapControlsAssembler
    from ui.handlers.map_interaction_handler import MapInteractionHandler
    from ui.router.map_event_router import MapEventRouter

    interaction_handler = MapInteractionHandler(800, 600, on_update_callback=MagicMock())
    street_handler = MapComponentsFactory.create_street_interaction_handler()
    event_router = MapEventRouter(
        interaction_handler=interaction_handler,
        street_interaction_handler=street_handler,
        safe_update_callback=MagicMock(),
    )
    controls_assembler = MapControlsAssembler()

    result = builder.build_scene(
        map_data=sample_map_data,
        viewport_width=800,
        viewport_height=600,
        map_stack=mock_stack,
        telemetry_manager=mock_telemetry,
        visual_syncer=mock_syncer,
        controls_assembler=controls_assembler,
        interaction_handler=interaction_handler,
        street_interaction_handler=street_handler,
        event_router=event_router,
        widget_to_update=mock_widget,
    )

    assert result.canvas is not None
    assert result.drawer is not None
    assert result.state_manager is not None
    assert result.animator is not None
    assert len(result.stack_controls) > 0

    result.animator.stop()
