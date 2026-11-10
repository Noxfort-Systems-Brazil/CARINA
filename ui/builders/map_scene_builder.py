# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Defines the MapSceneBuilder.

Encapsulates the entire scene assembly and rebuild pipeline for the live vector map,
isolating geometry transformations, element assembly, and manager wiring from UI widgets.
"""

from dataclasses import dataclass
import logging
import os
from typing import Any, Callable, Dict, List, Optional, Tuple

import flet as ft
import flet.canvas as cv

from ui.builders.map_components_factory import MapComponentsFactory
from ui.interfaces.map_protocols import (
    EventRouterProtocol,
    InteractionHandlerProtocol,
    MapAnimatorProtocol,
    MapControlsAssemblerProtocol,
    MapDrawerProtocol,
    MapStateManagerProtocol,
    MapTelemetryManagerProtocol,
    MapVisualSyncerProtocol,
    StreetInteractionHandlerProtocol,
)


@dataclass
class MapSceneResult:
    canvas: cv.Canvas
    stack_controls: List[ft.Control]
    drawer: MapDrawerProtocol
    state_manager: MapStateManagerProtocol
    animator: MapAnimatorProtocol


class MapSceneBuilder:
    """
    Builder responsible for assembling all graphical and interactive sub-components of the map scene.
    Adheres strictly to SRP and Builder pattern principles.
    """

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
    ) -> MapSceneResult:
        """Executes the full map assembly and wiring pipeline."""
        nodes, edges, _ = map_data

        # 1. Recover active overrides and selection state
        street_overrides, semaphore_overrides = ({}, {})
        selected_type, selected_id = (None, None)

        if current_animator:
            street_overrides, semaphore_overrides = current_animator.get_active_overrides()
            if hasattr(current_animator, "latest_congestion_data") and current_animator.latest_congestion_data:
                telemetry_manager.merge_congestion_data(current_animator.latest_congestion_data)
            if hasattr(current_animator, "latest_panel_data") and current_animator.latest_panel_data:
                telemetry_manager.merge_panel_data(current_animator.latest_panel_data)
            current_animator.stop()

        if current_state_manager:
            selected_type, selected_id = current_state_manager.get_selected_type_and_id()

        # 2. Initialize Canvas and interaction handler viewport dimensions
        canvas = cv.Canvas(shapes=[], width=viewport_width, height=viewport_height)
        map_stack.width = viewport_width
        map_stack.height = viewport_height
        interaction_handler.base_width = viewport_width
        interaction_handler.base_height = viewport_height

        # 3. Create drawer and compute coordinate transformations
        drawer = MapComponentsFactory.create_drawer(nodes, edges)
        drawer.calculate_transformations(viewport_width, viewport_height)

        # 4. Draw initial road vector paths
        congestion_data = telemetry_manager.get_congestion_data()
        panel_data = telemetry_manager.get_panel_data()

        edge_paths = drawer.draw_initial_map(canvas, stroke_width=7.0, initial_congestion=congestion_data)
        street_interaction_handler.load_paths(edge_paths)

        # 5. Assemble canvas and interactive widgets (with CartoDB basemap if present and enabled)
        background_ctrl = None
        try:
            from ui.builders.map_background_builder import MapBackgroundBuilder

            if MapBackgroundBuilder.ENABLED:
                from ui.loader.map_asset_loader import MapAssetLoader

                loader = MapAssetLoader()
                basemap_path = loader.get_asset_path("maps", "basemap_positron.png")
                if not basemap_path or not os.path.exists(basemap_path) or os.path.getsize(basemap_path) == 0:
                    basemap_path = loader.ensure_basemap_present()
                if basemap_path and os.path.exists(basemap_path):
                    background_ctrl = MapBackgroundBuilder.build(basemap_path, drawer)
        except Exception as bg_err:
            logging.debug(f"[MapSceneBuilder] Basemap não aplicado: {bg_err}")

        stack_controls, interactive_widgets_map = controls_assembler.assemble_map_controls(
            drawer=drawer, canvas=canvas, background_control=background_ctrl
        )
        map_stack.controls = stack_controls

        # 6. Create state manager and restore selection
        state_manager = MapComponentsFactory.create_state_manager(
            canvas=canvas, stack=map_stack, edge_paths=edge_paths, interactive_widgets=interactive_widgets_map
        )
        if selected_type and selected_id:
            state_manager.set_selection(selected_type, selected_id)

        # 7. Create animator
        animator = MapComponentsFactory.create_animator(
            widget_to_update=widget_to_update,
            get_panel_state_callback=get_panel_state_callback,
            on_panel_update_callback=on_panel_update_callback,
            edge_paths=edge_paths,
            interactive_widgets=interactive_widgets_map,
            topology_edges=edges,
            initial_congestion_data=congestion_data.copy(),
            initial_panel_data=panel_data.copy(),
            initial_street_overrides=street_overrides,
            initial_semaphore_overrides=semaphore_overrides,
            vehicle_markers=getattr(widget_to_update, "vehicle_markers", None),
        )

        # 8. Synchronize cached visuals immediately
        visual_syncer.sync_cached_visuals(
            edge_paths=edge_paths,
            interactive_widgets_map=interactive_widgets_map,
            topology_edges=edges,
            congestion_data=congestion_data,
            street_overrides=street_overrides,
            semaphore_overrides=semaphore_overrides,
            panel_data=panel_data,
        )

        # 9. Connect event router and start background animator
        event_router.attach_managers(state_manager, animator)
        animator.start()

        return MapSceneResult(
            canvas=canvas, stack_controls=stack_controls, drawer=drawer, state_manager=state_manager, animator=animator
        )
