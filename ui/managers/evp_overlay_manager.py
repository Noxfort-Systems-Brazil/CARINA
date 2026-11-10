# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import math
from typing import Any, Callable, Dict, Optional, Tuple

import flet as ft
from ui.widgets.evp_vehicle_marker import EVPVehicleMarker


class EVPOverlayManager:
    """
    Manages the lifecycle, geographic projection, and visual markers of emergency vehicles
    displayed over the live canvas map.
    """

    def __init__(
        self,
        map_stack: ft.Stack,
        get_drawer: Callable[[], Any],
        get_viewport_manager: Callable[[], Any],
        get_animator: Callable[[], Any],
        on_vehicle_click: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_update_callback: Optional[Callable[[], None]] = None,
    ):
        self.map_stack = map_stack
        self.get_drawer = get_drawer
        self.get_viewport_manager = get_viewport_manager
        self.get_animator = get_animator
        self.on_vehicle_click = on_vehicle_click
        self.on_update_callback = on_update_callback
        self.vehicle_markers: Dict[str, EVPVehicleMarker] = {}

    def mount(self) -> None:
        """Subscribes to asynchronous telemetry events from EVPNotifier."""
        try:
            from src.evp.evp_notifier import EVPNotifier
            EVPNotifier.get_instance().register_listener(self.handle_evp_telemetry)
        except Exception as e:
            logging.debug(f"[EVPOverlayManager] EVPNotifier registration notice: {e}")

        # Immediately synchronize active vehicles already connected to EVPService
        try:
            from src.evp.evp_service import EVPService
            for vehicle_data in EVPService.get_instance().get_all_vehicles():
                if vehicle_data.get("is_online", False):
                    self.handle_evp_telemetry(vehicle_data)
        except Exception as e:
            logging.debug(f"[EVPOverlayManager] Erro ao sincronizar viaturas ativas no mount: {e}")

    def unmount(self) -> None:
        """Unsubscribes from EVPNotifier."""
        try:
            from src.evp.evp_notifier import EVPNotifier
            EVPNotifier.get_instance().unregister_listener(self.handle_evp_telemetry)
        except Exception:
            pass

    def reattach_markers_to_stack(self, new_stack: Optional[ft.Stack] = None) -> None:
        """Reattaches active vehicle markers if the canvas scene or stack was rebuilt."""
        target_stack = new_stack or self.map_stack
        if self.vehicle_markers:
            for marker in self.vehicle_markers.values():
                if marker not in target_stack.controls:
                    target_stack.controls.append(marker)

    def project_vehicle_to_canvas(
        self, lat: float, lon: float, active_int_id: Optional[str] = None
    ) -> Tuple[float, float]:
        """Converts geographic coordinates (WGS84) to Flet Canvas pixel coordinates."""
        drawer = self.get_drawer()
        viewport_manager = self.get_viewport_manager()

        if not drawer or not getattr(drawer, "nodes", None):
            width = getattr(viewport_manager, "width", 800.0)
            height = getattr(viewport_manager, "height", 600.0)
            return (width / 2.0, height / 2.0)

        # 1. Attempt direct geodetic projection via EVPTopologyService (UTM / origBoundary -> SUMO local)
        try:
            from src.evp.evp_service import EVPService
            topo = EVPService.get_instance().topology_service
            sumo_x, sumo_y = topo.lat_lon_to_sumo(lat, lon)
            if (sumo_x, sumo_y) != (lon, lat) or (abs(lat) > 90.0 or abs(lon) > 180.0):
                return drawer.transform_point(sumo_x, sumo_y)
        except Exception as ex:
            logging.debug(f"[EVPOverlayManager] Falha na projeção via EVPTopologyService: {ex}")

        # 2. Geodetic anchor node fallback
        anchor_node = None
        anchor_geo = None

        try:
            from src.evp.evp_service import EVPService
            intersections_geo = EVPService.get_instance()._intersections_geo
        except Exception:
            intersections_geo = {}

        if active_int_id and active_int_id in drawer.nodes and active_int_id in intersections_geo:
            anchor_node = drawer.nodes[active_int_id]
            anchor_geo = intersections_geo[active_int_id]
        else:
            for int_id, geo in intersections_geo.items():
                if int_id in drawer.nodes:
                    anchor_node = drawer.nodes[int_id]
                    anchor_geo = geo
                    break

        if anchor_node and anchor_geo:
            ref_lat, ref_lon = anchor_geo
            if abs(ref_lat) <= 90.0 and abs(ref_lon) <= 180.0 and abs(lat) <= 90.0 and abs(lon) <= 180.0:
                ref_x, ref_y = anchor_node["x"], anchor_node["y"]
                meters_lat = (lat - ref_lat) * 111139.0
                meters_lon = (lon - ref_lon) * 111139.0 * math.cos(math.radians(ref_lat))
                sumo_x = ref_x + meters_lon
                sumo_y = ref_y + meters_lat
                return drawer.transform_point(sumo_x, sumo_y)

        # Coordinates already in SUMO metric space
        if abs(lat) > 90.0 or abs(lon) > 180.0:
            return drawer.transform_point(float(lon), float(lat))

        return drawer.transform_point(drawer.sumo_center_x, drawer.sumo_center_y)

    def handle_evp_telemetry(self, vehicle_data: Dict[str, Any]) -> None:
        """Processes telemetry payload and updates or instantiates vehicle markers."""
        try:
            v_id = vehicle_data.get("vehicle_id", "V1")
            corp = vehicle_data.get("corporation", "POLICIA")
            lat = float(vehicle_data.get("latitude", 0.0))
            lon = float(vehicle_data.get("longitude", 0.0))
            speed = float(vehicle_data.get("speed_kmh", 0.0))
            heading = float(vehicle_data.get("heading_deg", 0.0))
            siren = bool(vehicle_data.get("siren_active", False))
            is_evp_triggered = bool(vehicle_data.get("is_evp_triggered", False))
            active_int = vehicle_data.get("active_intersection_id")
            is_online = bool(vehicle_data.get("is_online", True))
            action = vehicle_data.get("action", "")

            # If vehicle is explicitly deleted or offline, remove marker to keep map uncluttered
            if action == "deleted" or not is_online:
                if v_id in self.vehicle_markers:
                    marker = self.vehicle_markers.pop(v_id)
                    if marker in self.map_stack.controls:
                        self.map_stack.controls.remove(marker)
                    if self.on_update_callback:
                        self.on_update_callback()
                return

            cx, cy = self.project_vehicle_to_canvas(lat, lon, active_int)

            animator = self.get_animator()
            blink_state = getattr(animator, "blink_toggle", False) if animator else False

            if v_id in self.vehicle_markers:
                marker = self.vehicle_markers[v_id]
                marker.visible = True
                marker.left = cx - (marker.width / 2.0)
                marker.top = cy - (marker.height / 2.0)
                marker.update_state(lat, lon, speed, heading, siren, blink_state, is_evp_triggered=is_evp_triggered)
            else:
                marker = EVPVehicleMarker(
                    vehicle_id=v_id,
                    corporation=corp,
                    initial_lat=lat,
                    initial_lon=lon,
                    siren_active=siren,
                    is_evp_triggered=is_evp_triggered,
                    speed_kmh=speed,
                    heading_deg=heading,
                    on_click_callback=self._handle_marker_click,
                )
                marker.visible = True
                marker.left = cx - (marker.width / 2.0)
                marker.top = cy - (marker.height / 2.0)
                self.vehicle_markers[v_id] = marker
                if marker not in self.map_stack.controls:
                    self.map_stack.controls.append(marker)

            if self.on_update_callback:
                self.on_update_callback()
        except Exception as e:
            logging.error(f"[EVPOverlayManager] Error processing EVP telemetry: {e}", exc_info=True)

    def _handle_marker_click(self, vehicle_data: Dict[str, Any]) -> None:
        if self.on_vehicle_click:
            self.on_vehicle_click(vehicle_data)
