# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from unittest.mock import MagicMock

import flet as ft
import flet.canvas as cv
import pytest

from ui.handlers.map_interaction_handler import MapInteractionHandler
from ui.handlers.street_interaction_handler import StreetInteractionHandler
from ui.managers.map_state_manager import MapStateManager
from ui.router.map_event_router import MapEventRouter


class FakeTapEvent:
    def __init__(self, local_x: float, local_y: float):
        self.local_x = local_x
        self.local_y = local_y


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


def test_traffic_light_border_and_light_hit_over_street():
    """Validates that clicks on traffic light borders and individual lights (red/yellow/green)
    always select the traffic light even when a street passes directly underneath."""
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

    # Traffic light centered at (100, 100), width=20, height=50:
    # bounds are left=90, right=110, top=75, bottom=125
    mock_tl = ft.Container(width=20, height=50, left=90, top=75)
    interactive_widgets = {"tl_1": mock_tl}

    # Road passing directly underneath at y=100: from (0, 100) to (300, 100)
    road_path = cv.Path([cv.Path.MoveTo(0, 100), cv.Path.LineTo(300, 100)])
    street_handler.load_paths({"edge_main": road_path})

    state_manager = MapStateManager(
        canvas=MagicMock(spec=cv.Canvas, shapes=[]),
        stack=MagicMock(spec=ft.Stack, controls=[]),
        edge_paths={"edge_main": road_path},
        interactive_widgets=interactive_widgets,
    )
    router.attach_managers(state_manager=state_manager, animator=None)

    # 1. Top light (red light) at (100, 80)
    router.handle_map_tap(FakeTapEvent(100.0, 80.0))
    on_tl_clicked.assert_called_with("tl_1")
    assert state_manager.selected_interactive_id == "tl_1"
    assert state_manager.selected_edge_id is None

    # Reset selection for next check
    state_manager.set_selection(None, None)

    # 2. Bottom light (green light) at (100, 120)
    router.handle_map_tap(FakeTapEvent(100.0, 120.0))
    on_tl_clicked.assert_called_with("tl_1")
    assert state_manager.selected_interactive_id == "tl_1"

    # Reset selection
    state_manager.set_selection(None, None)

    # 3. Exact left border at (90, 100) directly on the road
    router.handle_map_tap(FakeTapEvent(90.0, 100.0))
    on_tl_clicked.assert_called_with("tl_1")
    assert state_manager.selected_interactive_id == "tl_1"

    # Reset selection
    state_manager.set_selection(None, None)

    # 4. Exact right border at (110, 100) directly on the road
    router.handle_map_tap(FakeTapEvent(110.0, 100.0))
    on_tl_clicked.assert_called_with("tl_1")
    assert state_manager.selected_interactive_id == "tl_1"

    # Reset selection
    state_manager.set_selection(None, None)

    # 5. Hit padding zone (88, 100) -> 2px outside left border, on road
    router.handle_map_tap(FakeTapEvent(88.0, 100.0))
    on_tl_clicked.assert_called_with("tl_1")
    assert state_manager.selected_interactive_id == "tl_1"

    # Reset selection
    state_manager.set_selection(None, None)

    # 6. Hit padding zone (112, 100) -> 2px outside right border, on road
    router.handle_map_tap(FakeTapEvent(112.0, 100.0))
    on_tl_clicked.assert_called_with("tl_1")
    assert state_manager.selected_interactive_id == "tl_1"

    # Reset selection
    state_manager.set_selection(None, None)

    # 7. Beyond padding zone at (115, 100) -> 5px outside right border, on road -> must select road
    router.handle_map_tap(FakeTapEvent(115.0, 100.0))
    on_st_clicked.assert_called_with("edge_main")
    assert state_manager.selected_edge_id == "edge_main"
    assert state_manager.selected_interactive_id is None
