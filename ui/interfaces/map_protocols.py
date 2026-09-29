# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Noxfort Systems
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
# along with this program. If not, see <https://www.gnu.org/licenses/>.

# File: ui/interfaces/map_protocols.py
# Author: Gabriel Moraes
# Date: 2026-06-19

from typing import Any, Callable, Dict, List, Optional, Protocol, Tuple, runtime_checkable

import flet as ft
import flet.canvas as cv


@runtime_checkable
class InteractionHandlerProtocol(Protocol):
    """Protocol defining the map pan/zoom interaction contract."""

    scale: ft.Scale
    offset: ft.Offset
    base_width: float
    base_height: float

    def center_and_reset_zoom(self) -> None: ...

    def handle_pan_update(self, e: ft.DragUpdateEvent) -> None: ...

    def handle_zoom(self, e: ft.ScrollEvent, mouse_x: float = None, mouse_y: float = None) -> None: ...

    def get_map_coordinates(self, local_x: float, local_y: float) -> Tuple[float, float]: ...


@runtime_checkable
class StreetInteractionHandlerProtocol(Protocol):
    """Protocol defining street selection and click detection contract."""

    edge_paths: Dict[str, cv.Path]
    selected_edge_id: str | None
    base_hit_threshold: float

    def load_paths(self, edge_paths: Dict[str, cv.Path]) -> None: ...

    def find_closest_edge(self, click_x: float, click_y: float) -> Tuple[str | None, float]: ...

    def select_edge(self, edge_id: str | None) -> None: ...

    def handle_click(self, click_x: float, click_y: float, current_scale: float) -> None: ...


@runtime_checkable
class EventRouterProtocol(Protocol):
    """Protocol defining how events are dispatched from the map."""

    def handle_map_tap(self, e: ft.TapEvent) -> None: ...

    def handle_street_click(self, street_id: str | None) -> None: ...

    def set_semaphore_override_state(self, semaphore_id: str, state: str) -> None: ...

    def set_street_override_state(self, street_id: str, state: str) -> None: ...

    def attach_managers(self, map_state_manager: Any, animator: Any) -> None: ...


@runtime_checkable
class MapDrawerProtocol(Protocol):
    """Protocol defining the vector map rendering contract."""

    nodes: Dict[str, Dict]
    edges: List[Dict]

    def calculate_transformations(self, view_width: int, view_height: int) -> None: ...

    def draw_initial_map(
        self, canvas: cv.Canvas, stroke_width: float, initial_congestion: Dict[str, Any] = None
    ) -> Dict[str, cv.Path]: ...

    def transform_point(self, sumo_x: float, sumo_y: float) -> Tuple[float, float]: ...


@runtime_checkable
class MapStateManagerProtocol(Protocol):
    """Protocol defining selection state management on the map."""

    selected_edge_id: str | None
    selected_interactive_id: str | None
    interactive_widgets: Dict[str, Any]

    def check_widget_hit(self, x: float, y: float) -> str | None: ...

    def get_closest_widget_distance(self, x: float, y: float) -> Tuple[str | None, float]: ...

    def set_selection(self, item_type: str | None, item_id: str | None) -> None: ...

    def get_selected_type_and_id(self) -> Tuple[str | None, str | None]: ...


@runtime_checkable
class MapAnimatorProtocol(Protocol):
    """Protocol defining simulation animation contract."""

    edge_paths: Dict[str, cv.Path]
    override_manager: Any

    def start(self) -> None: ...

    def stop(self) -> None: ...

    def update_data(self, data_packet: dict) -> None: ...

    def get_active_overrides(self) -> Tuple[Dict[str, str], Dict[str, str]]: ...


@runtime_checkable
class MapViewportManagerProtocol(Protocol):
    """Protocol defining viewport dimension calculations."""

    width: int
    height: int

    def calculate_dimensions(self, page_width: float | None, page_height: float | None) -> Tuple[int, int]: ...


@runtime_checkable
class MapControlsAssemblerProtocol(Protocol):
    """Protocol defining interactive controls assembler."""

    def assemble_map_controls(
        self, drawer: MapDrawerProtocol, canvas: cv.Canvas
    ) -> Tuple[List[ft.Control], Dict[str, Any]]: ...


@runtime_checkable
class MapTelemetryManagerProtocol(Protocol):
    """Protocol defining telemetry storage and cache contract."""

    def update_from_packet(self, data_packet: Dict[str, Any]) -> None: ...

    def get_congestion_data(self) -> Dict[str, Any]: ...

    def get_panel_data(self) -> Dict[str, Any]: ...

    def get_street_data(self) -> Dict[str, Any]: ...

    def clear(self) -> None: ...


@runtime_checkable
class MapVisualSyncerProtocol(Protocol):
    """Protocol defining initial/cached visual synchronization contract."""

    def sync_cached_visuals(
        self,
        edge_paths: Dict[str, cv.Path],
        interactive_widgets_map: Dict[str, Any],
        topology_edges: List[Dict[str, Any]],
        congestion_data: Dict[str, Any],
        street_overrides: Dict[str, str],
        semaphore_overrides: Dict[str, str],
        panel_data: Dict[str, Any],
    ) -> None: ...


@runtime_checkable
class MapSceneBuilderProtocol(Protocol):
    """Protocol defining the full map scene assembly and rebuild pipeline contract."""

    def build_scene(
        self,
        map_data: Tuple,
        viewport_width: int,
        viewport_height: int,
        map_stack: ft.Stack,
        telemetry_manager: MapTelemetryManagerProtocol,
        visual_syncer: MapVisualSyncerProtocol,
        controls_assembler: MapControlsAssemblerProtocol,
        interaction_handler: InteractionHandlerProtocol,
        street_interaction_handler: StreetInteractionHandlerProtocol,
        event_router: EventRouterProtocol,
        widget_to_update: ft.Control,
        get_panel_state_callback: Optional[Callable[[], Dict]] = None,
        on_panel_update_callback: Optional[Callable[[str, Dict, str, str], None]] = None,
        current_animator: Optional[MapAnimatorProtocol] = None,
        current_state_manager: Optional[MapStateManagerProtocol] = None,
    ) -> Any: ...
