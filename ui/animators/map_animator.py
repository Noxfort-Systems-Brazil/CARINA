# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Defines the MapAnimator class.

Orchestrates the high-frequency visual updates of interactive map and details panel elements.
"""

import logging
import threading
import time
from typing import Any, Callable, Dict, List, Tuple

import flet as ft
import flet.canvas as cv

from ui.animators.street_heatmap_updater import StreetHeatmapUpdater
from ui.managers.override_state_manager import OverrideStateManager


class MapAnimator:
    """
    Manages a background thread to apply high-frequency visual updates.
    Adheres strictly to SRP and OCP.
    """

    def __init__(
        self,
        widget_to_update: ft.Control,
        get_panel_state_callback: Callable[[], Dict] = None,
        on_panel_update_callback: Callable[[str, Dict, str, str], None] = None,
        edge_paths: Dict[str, cv.Path] = None,
        semaforo_widgets: Dict[str, Any] = None,
        interval: float = 0.5,
        topology_edges: List[Dict] = None,
        initial_congestion_data: Dict[str, Any] = None,
        initial_panel_data: Dict[str, Any] = None,
        initial_street_overrides: Dict[str, str] = None,
        initial_semaphore_overrides: Dict[str, str] = None,
        vehicle_markers: Dict[str, Any] = None,
    ):
        self.widget = widget_to_update
        self.get_panel_state_callback = get_panel_state_callback
        self.on_panel_update_callback = on_panel_update_callback
        self.edge_paths = edge_paths or {}
        self.interactive_widgets = semaforo_widgets or {}
        self.vehicle_markers = vehicle_markers if vehicle_markers is not None else {}
        self.interval = interval

        self.topology_edges = topology_edges or []
        self.edge_group_map = StreetHeatmapUpdater.build_edge_group_map(self.topology_edges)

        self.thread = None
        self.is_running = False

        self.data_lock = threading.Lock()
        self.latest_congestion_data: Dict[str, Any] = initial_congestion_data.copy() if initial_congestion_data else {}
        self.latest_panel_data: Dict[str, Any] = initial_panel_data.copy() if initial_panel_data else {}

        self.override_manager = OverrideStateManager()
        if initial_street_overrides:
            self.override_manager.street_overrides.update(initial_street_overrides)
        if initial_semaphore_overrides:
            self.override_manager.semaphore_overrides.update(initial_semaphore_overrides)

        self.command_queue = self.override_manager.command_queue
        self.blink_toggle = False
        self.last_update_time = 0
        self.throttle_interval = 0.1

    def start(self):
        if not self.thread or not self.thread.is_alive():
            self.is_running = True
            self.thread = threading.Thread(target=self._updater_loop, daemon=True)
            self.thread.start()
            logging.info("[MapAnimator] Animation thread started.")

    def stop(self):
        self.is_running = False
        logging.info("[MapAnimator] Signal sent to stop the animation thread.")

    def update_data(self, data_packet: dict):
        with self.data_lock:
            packet_type = data_packet.get("type", "unknown")

            if packet_type == "initial_map_geometry":
                congestion = data_packet.get("congestion_update", {})
                if congestion:
                    self.latest_congestion_data.update(congestion)
            elif packet_type in ["congestion_update", "update_dashboard_data"]:
                payload = data_packet.get("payload", {})
                if isinstance(payload, dict) and payload:
                    self.latest_congestion_data.update(payload)

            if "panel_data" in data_packet and data_packet["panel_data"]:
                self.latest_panel_data.update(data_packet["panel_data"])

    def get_active_overrides(self) -> Tuple[Dict[str, str], Dict[str, str]]:
        """Processes pending queue commands and returns a copy of (street_overrides, semaphore_overrides)."""
        if hasattr(self, "override_manager") and self.override_manager:
            self.override_manager.process_queue()
            return (
                self.override_manager.get_street_overrides().copy(),
                self.override_manager.get_semaphore_overrides().copy(),
            )
        return ({}, {})

    def _updater_loop(self):
        """The main loop that reads the latest telemetry and applies visual updates."""
        while self.is_running:
            try:
                self.blink_toggle = not self.blink_toggle

                with self.data_lock:
                    congestion_to_render = self.latest_congestion_data.copy()
                    panel_data_to_render = self.latest_panel_data.copy()

                self.override_manager.process_queue()
                street_overrides = self.override_manager.get_street_overrides()
                semaphore_overrides = self.override_manager.get_semaphore_overrides()

                current_time = time.time()
                should_update_congestion = (current_time - self.last_update_time) >= self.throttle_interval

                if should_update_congestion and self.edge_paths and congestion_to_render:
                    StreetHeatmapUpdater.update_edge_paths(
                        edge_paths=self.edge_paths,
                        edge_group_map=self.edge_group_map,
                        congestion_data=congestion_to_render,
                        street_overrides=street_overrides,
                    )
                    self.last_update_time = current_time

                if self.interactive_widgets and panel_data_to_render:
                    for widget_id, widget in self.interactive_widgets.items():
                        if hasattr(widget, "apply_telemetry"):
                            widget.apply_telemetry(panel_data_to_render, semaphore_overrides, self.blink_toggle)

                if self.vehicle_markers:
                    for marker in list(self.vehicle_markers.values()):
                        is_alert = getattr(marker, "siren_active", False) or getattr(marker, "is_evp_triggered", False)
                        if is_alert:
                            marker.update_state(
                                marker.latitude,
                                marker.longitude,
                                marker.speed_kmh,
                                marker.heading_deg,
                                marker.siren_active,
                                self.blink_toggle,
                                is_evp_triggered=getattr(marker, "is_evp_triggered", False),
                            )
                            try:
                                if getattr(marker, "page", None):
                                    marker.update()
                            except Exception:
                                pass

                if self.get_panel_state_callback and self.on_panel_update_callback:
                    panel_state = self.get_panel_state_callback()
                    selected_id = panel_state.get("selected_id")
                    is_panel_visible = panel_state.get("is_panel_visible", False)

                    if selected_id and is_panel_visible:
                        semaphore_data = panel_data_to_render.get(selected_id, {})
                        override_state = semaphore_overrides.get(selected_id)
                        if override_state:
                            semaphore_data = semaphore_data.copy() if semaphore_data else {}
                            lanes_state = semaphore_data.get("lanes_state", {}).copy()

                            if override_state == "ALERT":
                                blink_char = "y" if self.blink_toggle else "o"
                                for lane in lanes_state:
                                    lanes_state[lane] = blink_char
                                semaphore_data["display_state"] = "YELLOW"
                            elif override_state == "OFF":
                                for lane in lanes_state:
                                    lanes_state[lane] = "o"
                                semaphore_data["display_state"] = "OFF"

                            semaphore_data["lanes_state"] = lanes_state

                        phase = panel_state.get("phase", "UNKNOWN")
                        mode = panel_state.get("mode", "UNKNOWN")
                        self.on_panel_update_callback(selected_id, semaphore_data, phase, mode)

                if self.widget and getattr(self.widget, "page", None):
                    try:
                        self.widget.update()
                    except AssertionError:
                        pass
                    try:
                        if hasattr(self.widget, "canvas") and getattr(self.widget.canvas, "page", None):
                            self.widget.canvas.update()
                    except AssertionError:
                        pass

                time.sleep(self.interval)

            except RuntimeError as e:
                if "Event loop is closed" in str(e) or "shutdown" in str(e):
                    logging.info("[MapAnimator Thread] Flet Event Loop closed. Stopping animations.")
                    self.is_running = False
                    break
                else:
                    logging.error(f"[MapAnimator Thread] Unexpected Runtime error: {e}")
            except Exception as e:
                logging.error(f"[MapAnimator Thread] Error: {e}. Stopping thread.", exc_info=True)
                self.is_running = False
                break
