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


def test_tap_under_zoom_and_pan_offset():
    """Validates that click routing resolves correctly when the canvas is zoomed and panned."""
    W, H = 800.0, 600.0
    scale = 1.5
    off_x, off_y = 0.1, -0.05
    cx, cy = W / 2.0, H / 2.0

    interaction_handler = MapInteractionHandler(W, H, on_update_callback=MagicMock())
    interaction_handler.scale.scale = scale
    interaction_handler.offset.x = off_x
    interaction_handler.offset.y = off_y

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

    # Traffic light in map space at (200, 200), width=20, height=50:
    # left=190, top=175
    mock_tl = ft.Container(width=20, height=50, left=190, top=175)
    interactive_widgets = {"tl_zoomed": mock_tl}

    # Road in map space from (0, 200) to (500, 200)
    road_path = cv.Path([cv.Path.MoveTo(0, 200), cv.Path.LineTo(500, 200)])
    street_handler.load_paths({"edge_zoomed": road_path})

    state_manager = MapStateManager(
        canvas=MagicMock(spec=cv.Canvas, shapes=[]),
        stack=MagicMock(spec=ft.Stack, controls=[]),
        edge_paths={"edge_zoomed": road_path},
        interactive_widgets=interactive_widgets,
    )
    router.attach_managers(state_manager=state_manager, animator=None)

    # 1. Click on traffic light center in map space (200, 200)
    screen_tl_x = (200.0 - cx) * scale + cx + (off_x * W)
    screen_tl_y = (200.0 - cy) * scale + cy + (off_y * H)

    router.handle_map_tap(FakeTapEvent(screen_tl_x, screen_tl_y))
    on_tl_clicked.assert_called_with("tl_zoomed")
    assert state_manager.selected_interactive_id == "tl_zoomed"

    # Reset
    state_manager.set_selection(None, None)

    # 2. Click on road away from traffic light: map space (350, 200)
    screen_rd_x = (350.0 - cx) * scale + cx + (off_x * W)
    screen_rd_y = (200.0 - cy) * scale + cy + (off_y * H)

    router.handle_map_tap(FakeTapEvent(screen_rd_x, screen_rd_y))
    on_st_clicked.assert_called_with("edge_zoomed")
    assert state_manager.selected_edge_id == "edge_zoomed"


def test_traffic_light_off_center_tap_within_tolerance():
    """Validates that clicking slightly off-center (e.g. 12px away) reliably selects traffic light."""
    interaction_handler = MapInteractionHandler(800.0, 600.0, on_update_callback=MagicMock())
    street_handler = StreetInteractionHandler(on_street_selected=MagicMock())
    on_tl_clicked = MagicMock()

    router = MapEventRouter(
        interaction_handler=interaction_handler,
        street_interaction_handler=street_handler,
        safe_update_callback=MagicMock(),
        on_semaphore_click=on_tl_clicked,
        on_street_click=MagicMock(),
    )
    street_handler.on_street_selected = router.handle_street_click

    # Traffic light at (300, 300), width=20, height=50:
    # left=290, top=275, right=310, bottom=325
    mock_tl = ft.Container(width=20, height=50, left=290, top=275)
    interactive_widgets = {"tl_isolated": mock_tl}

    state_manager = MapStateManager(
        canvas=MagicMock(spec=cv.Canvas, shapes=[]),
        stack=MagicMock(spec=ft.Stack, controls=[]),
        edge_paths={},
        interactive_widgets=interactive_widgets,
    )
    router.attach_managers(state_manager=state_manager, animator=None)

    # Click 12px to the left of the bounding box at (278, 300)
    router.handle_map_tap(FakeTapEvent(278.0, 300.0))
    on_tl_clicked.assert_called_with("tl_isolated")
    assert state_manager.selected_interactive_id == "tl_isolated"
