# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Defines the LiveCanvasMapWidget.
Pure UI Facade orchestrating map drawing, animation, telemetry, and interactions.
"""

import logging
from typing import Any, Callable, Dict, Tuple

import flet as ft
import flet.canvas as cv

from ui.builders.map_components_factory import MapComponentsFactory
from ui.builders.map_gesture_builder import MapGestureBuilder
from ui.handlers.locale_manager import LocaleManager
from ui.interfaces.map_protocols import (
    EventRouterProtocol,
    InteractionHandlerProtocol,
    MapAnimatorProtocol,
    MapControlsAssemblerProtocol,
    MapDrawerProtocol,
    MapSceneBuilderProtocol,
    MapStateManagerProtocol,
    MapTelemetryManagerProtocol,
    MapViewportManagerProtocol,
    MapVisualSyncerProtocol,
    StreetInteractionHandlerProtocol,
)
from ui.managers.evp_overlay_manager import EVPOverlayManager


class LiveCanvasMapWidget(ft.Container):
    """Pure UI Facade orchestrating map drawing, animation, telemetry, and interactions."""

    def __init__(
        self,
        locale_manager: LocaleManager,
        on_semaphore_click: Callable[[str | None], None] = None,
        on_street_click: Callable[[str | None], None] = None,
        get_panel_state_callback: Callable[[], Dict] = None,
        on_panel_update_callback: Callable[[str, Dict, str, str], None] = None,
        on_evp_vehicle_click: Callable[[Dict[str, Any]], None] = None,
        bgcolor: str = "#F7F7F7",
    ):
        super().__init__(
            expand=True,
            bgcolor=bgcolor,
            border_radius=10,
            alignment=ft.alignment.center,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
        )
        self.locale_manager = locale_manager
        self.get_panel_state_callback = get_panel_state_callback
        self.on_panel_update_callback = on_panel_update_callback
        self.on_evp_vehicle_click = on_evp_vehicle_click

        # Specialized collaborators instantiated via Factory
        self.viewport_manager: MapViewportManagerProtocol = MapComponentsFactory.create_viewport_manager()
        self.controls_assembler: MapControlsAssemblerProtocol = MapComponentsFactory.create_controls_assembler()
        self.telemetry_manager: MapTelemetryManagerProtocol = MapComponentsFactory.create_telemetry_manager()
        self.visual_syncer: MapVisualSyncerProtocol = MapComponentsFactory.create_visual_syncer()
        self.scene_builder: MapSceneBuilderProtocol = MapComponentsFactory.create_scene_builder()

        self.interaction_handler: InteractionHandlerProtocol = MapComponentsFactory.create_interaction_handler(
            viewport_width=self.viewport_manager.width,
            viewport_height=self.viewport_manager.height,
            on_update=self._safe_update,
        )
        self.street_interaction_handler: StreetInteractionHandlerProtocol = (
            MapComponentsFactory.create_street_interaction_handler()
        )
        self.event_router: EventRouterProtocol = MapComponentsFactory.create_event_router(
            interaction_handler=self.interaction_handler,
            street_interaction_handler=self.street_interaction_handler,
            on_update=self._safe_update,
            on_semaphore_click=on_semaphore_click,
            on_street_click=on_street_click,
        )
        self.street_interaction_handler.on_street_selected = self.event_router.handle_street_click

        # Scene state references
        self.drawer: MapDrawerProtocol | None = None
        self.animator: MapAnimatorProtocol | None = None
        self.map_state_manager: MapStateManagerProtocol | None = None
        self._pending_map_data: Tuple | None = None
        self._is_map_built = False

        self.canvas = cv.Canvas(shapes=[], width=self.viewport_manager.width, height=self.viewport_manager.height)
        self.map_stack = ft.Stack(
            width=self.viewport_manager.width,
            height=self.viewport_manager.height,
            scale=self.interaction_handler.scale,
            offset=self.interaction_handler.offset,
        )

        self.gesture_builder = MapGestureBuilder(
            interaction_handler=self.interaction_handler,
            event_router=self.event_router,
            initial_x=self.viewport_manager.width / 2,
            initial_y=self.viewport_manager.height / 2,
        )
        self.gesture_detector = self.gesture_builder.build(self.map_stack)

        self.evp_overlay_manager = EVPOverlayManager(
            map_stack=self.map_stack,
            get_drawer=lambda: self.drawer,
            get_viewport_manager=lambda: self.viewport_manager,
            get_animator=lambda: self.animator,
            on_vehicle_click=self.on_evp_vehicle_click,
            on_update_callback=self._safe_update,
        )
        self.event_router.evp_overlay_manager = self.evp_overlay_manager

        self.content = ft.Column(
            [
                ft.ProgressRing(),
                ft.Text(self.locale_manager.get_string("live_map.waiting_scenario", default="Waiting for Scenario Connection...")),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

        self.did_mount = self._on_mount
        self.will_unmount = self.on_unmount

    # Telemetry Cache Delegates (Backwards Compatibility)
    @property
    def vehicle_markers(self) -> Dict[str, Any]: return self.evp_overlay_manager.vehicle_markers
    @property
    def _latest_congestion_data(self) -> Dict[str, Any]: return self.telemetry_manager.get_congestion_data()
    @property
    def _latest_panel_data(self) -> Dict[str, Any]: return self.telemetry_manager.get_panel_data()
    @property
    def _latest_street_data(self) -> Dict[str, Any]: return self.telemetry_manager.get_street_data()
    @property
    def last_mouse_x(self) -> float: return self.gesture_builder.last_mouse_x
    @last_mouse_x.setter
    def last_mouse_x(self, val: float): self.gesture_builder.last_mouse_x = val
    @property
    def last_mouse_y(self) -> float: return self.gesture_builder.last_mouse_y
    @last_mouse_y.setter
    def last_mouse_y(self, val: float): self.gesture_builder.last_mouse_y = val

    def _on_mount(self):
        self.evp_overlay_manager.mount()
        if self.page:
            MapGestureBuilder.setup_resize_listener(
                self.page,
                self.viewport_manager,
                lambda: self._build_map(self._pending_map_data) if self._pending_map_data else None,
            )
        self._calculate_dimensions()
        if self._pending_map_data:
            self._build_map(self._pending_map_data)

    def _calculate_dimensions(self):
        if self.page:
            pw, ph = self.page.width, self.page.height
            win = getattr(self.page, "window", None)
            if win:
                win_w, win_h = getattr(win, "width", None), getattr(win, "height", None)
                if isinstance(win_w, (int, float)) and win_w > 0: pw = win_w
                if isinstance(win_h, (int, float)) and win_h > 0: ph = win_h
            self.viewport_manager.calculate_dimensions(pw, ph)

    def update_translations(self, locale_manager: LocaleManager):
        self.locale_manager = locale_manager
        if isinstance(self.content, ft.Column) and len(self.content.controls) > 1 and isinstance(self.content.controls[1], ft.Text):
            self.content.controls[1].value = self.locale_manager.get_string("live_map.waiting_scenario", default="Waiting for Scenario Connection...")
        elif isinstance(self.content, ft.Text) and ("ERROR" in str(self.content.value) or "ERRO" in str(self.content.value)):
            self.content.value = self.locale_manager.get_string("live_map.error_geometry", default="ERROR: Map geometry data was not provided.")
        if self.page:
            self.update()

    def initialize_map(self, map_data: Tuple | None):
        if not map_data:
            err = self.locale_manager.get_string("live_map.error_geometry", default="ERROR: Map geometry data was not provided.")
            self.content = ft.Text(err, color=ft.Colors.RED)
            if self.page: self.update()
            return
        if self.page:
            self._calculate_dimensions()
            self._build_map(map_data)
        else:
            self._pending_map_data = map_data
            logging.info("[LiveCanvasMap] Map data received before mount. Deferred.")

    def clear_all_selections(self):
        if self.map_state_manager:
            self.map_state_manager.set_selection(item_type=None, item_id=None)
            self._safe_update()

    def update_data(self, data_packet: dict):
        self.telemetry_manager.update_from_packet(data_packet)
        if self.animator:
            self.animator.update_data(data_packet)

    def on_unmount(self):
        self.evp_overlay_manager.unmount()
        if self.animator:
            self.animator.stop()

    def set_semaphore_override_state(self, semaphore_id: str, state: str):
        self.event_router.set_semaphore_override_state(semaphore_id, state)

    def set_street_override_state(self, street_id: str, state: str):
        self.event_router.set_street_override_state(street_id, state)

    def _build_map(self, map_data: Tuple):
        self._pending_map_data = map_data
        scene_result = self.scene_builder.build_scene(
            map_data=map_data,
            viewport_width=self.viewport_manager.width,
            viewport_height=self.viewport_manager.height,
            map_stack=self.map_stack,
            telemetry_manager=self.telemetry_manager,
            visual_syncer=self.visual_syncer,
            controls_assembler=self.controls_assembler,
            interaction_handler=self.interaction_handler,
            street_interaction_handler=self.street_interaction_handler,
            event_router=self.event_router,
            widget_to_update=self,
            get_panel_state_callback=self.get_panel_state_callback,
            on_panel_update_callback=self.on_panel_update_callback,
            current_animator=self.animator,
            current_state_manager=self.map_state_manager,
        )

        self.canvas = scene_result.canvas
        self.drawer = scene_result.drawer
        self.map_state_manager = scene_result.state_manager
        self.animator = scene_result.animator
        self._is_map_built = True

        self.evp_overlay_manager.reattach_markers_to_stack(self.map_stack)
        self.content = self.gesture_detector
        if self.page:
            self.update()
        logging.info(f"[LiveCanvasMap] Map scene built ({self.viewport_manager.width}x{self.viewport_manager.height}).")

    def _safe_update(self):
        if not self.page:
            return
        for ctrl in (self.canvas, self.map_stack, self):
            try:
                if ctrl and getattr(ctrl, "page", None):
                    ctrl.update()
            except Exception:
                pass

    def _project_vehicle_to_canvas(self, lat: float, lon: float, active_int_id: str | None = None) -> Tuple[float, float]:
        return self.evp_overlay_manager.project_vehicle_to_canvas(lat, lon, active_int_id)

    def handle_evp_telemetry(self, vehicle_data: Dict[str, Any]):
        self.evp_overlay_manager.handle_evp_telemetry(vehicle_data)
