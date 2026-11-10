# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import Any, Dict, Optional

import flet as ft

from ui.clients.control_client import ControlClient
from ui.controllers.dashboard_data_coordinator import DashboardDataCoordinator
from ui.handlers.locale_manager import LocaleManager
from ui.loader.map_asset_loader import MapAssetLoader
from ui.widgets.control_panel_widget import ControlPanelWidget
from ui.widgets.evp_vehicle_card import EVPVehicleCard
from ui.widgets.live_canvas_map_widget import LiveCanvasMapWidget


class DashboardView(ft.Container):
    """Orchestrates the main live dashboard layout and user interactions."""

    def __init__(self, control_client: ControlClient, locale_manager: LocaleManager, security_ui=None):
        super().__init__(expand=True)
        self.locale_manager = locale_manager
        self.data_coordinator = DashboardDataCoordinator()

        self.current_mode = self.locale_manager.get_string("dashboard_view.mode_auto")
        self.selected_semaphore_id: Optional[str] = None
        self.selected_street_id: Optional[str] = None
        self.is_initialized = False

        self.control_panel = ControlPanelWidget(
            control_client=control_client,
            locale_manager=self.locale_manager,
            security_ui=security_ui,
            on_specific_command=self._handle_specific_command,
            on_street_override=self._handle_street_override,
            on_details_close=self._handle_panel_close,
            on_mode_change=self._handle_mode_change,
        )
        self.vehicle_card = EVPVehicleCard(on_close=self._handle_vehicle_card_close)
        self.map_widget = LiveCanvasMapWidget(
            locale_manager=self.locale_manager,
            on_semaphore_click=self._handle_semaphore_click,
            on_street_click=self._handle_street_click,
            get_panel_state_callback=self._get_panel_state,
            on_panel_update_callback=self._on_panel_update,
            on_evp_vehicle_click=self._handle_vehicle_click,
        )

        map_stack = ft.Stack(
            controls=[
                self.map_widget,
                ft.Container(content=self.vehicle_card, top=16, left=16),
            ],
            expand=True,
        )

        self.content = ft.Row(
            controls=[
                ft.Container(content=map_stack, alignment=ft.alignment.center, expand=True),
                self.control_panel,
            ],
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

        # Pre-initialize map geometry
        try:
            asset_loader = MapAssetLoader()
            map_data = asset_loader.load_map_data()
            if map_data:
                nodes, edges, _ = map_data
                self.data_coordinator.initialize_from_map_data(nodes, edges)
                self.map_widget.initialize_map(map_data)
                self.is_initialized = True
                try:
                    from src.evp.evp_service import EVPService
                    EVPService.get_instance().load_map_data(map_data)
                except Exception:
                    pass
        except Exception as err:
            logging.warning(f"[DashboardView] Error pre-loading map data: {err}", exc_info=True)

    # Backward compatibility properties
    @property
    def edge_names(self) -> Dict[str, str]: return self.data_coordinator.edge_names
    @edge_names.setter
    def edge_names(self, val: Dict[str, str]): self.data_coordinator.edge_names = val
    @property
    def maturity_phases(self) -> Dict[str, str]: return self.data_coordinator.maturity_phases
    @maturity_phases.setter
    def maturity_phases(self, val: Dict[str, str]): self.data_coordinator.maturity_phases = val
    @property
    def latest_data_packet(self) -> dict: return self.data_coordinator.latest_data_packet
    @latest_data_packet.setter
    def latest_data_packet(self, val: dict): self.data_coordinator.latest_data_packet = val
    @property
    def latest_panel_data(self) -> dict: return self.data_coordinator.latest_panel_data
    @latest_panel_data.setter
    def latest_panel_data(self, val: dict): self.data_coordinator.latest_panel_data = val
    @property
    def latest_street_data(self) -> dict: return self.data_coordinator.latest_street_data
    @latest_street_data.setter
    def latest_street_data(self, val: dict): self.data_coordinator.latest_street_data = val

    def _get_panel_state(self) -> Dict:
        return {
            "selected_id": self.selected_semaphore_id,
            "is_panel_visible": bool(getattr(getattr(self.control_panel, "specific_controls", None), "visible", False)),
            "phase": self.data_coordinator.maturity_phases.get(self.selected_semaphore_id, "UNKNOWN") if self.selected_semaphore_id else "UNKNOWN",
            "mode": self.current_mode,
        }

    def _on_panel_update(self, selected_id: str, semaphore_data: Dict, phase: str, mode: str):
        if semaphore_data and semaphore_data.get("brand") in (None, "Não informado"):
            try:
                from src.controller.connection_manager import HardwareConnectionManager
                hw_info = HardwareConnectionManager.get_global_hardware_info(selected_id)
                if hw_info and hw_info.get("brand") != "Não informado":
                    semaphore_data["brand"] = hw_info.get("brand")
                    semaphore_data["model"] = hw_info.get("model")
            except Exception:
                pass
        self.control_panel.exibir_controles_semaforo(selected_id, semaphore_data, phase, mode)

    def update_translations(self, lm: LocaleManager):
        self.current_mode = lm.get_string("dashboard_view.mode_auto")
        self.control_panel.update_translations(lm)
        self.map_widget.update_translations(lm)
        if self.page: self.update()

    def update_live_data(self, data_packet: dict):
        """Processes real-time data and updates UI caches and map scene."""
        if not self.is_initialized and data_packet.get("type") == "initial_map_geometry":
            self.is_initialized = True
            map_data = MapAssetLoader().load_map_data()
            if map_data:
                nodes, edges, _ = map_data
                self.data_coordinator.initialize_from_map_data(nodes, edges)
                self.map_widget.initialize_map(map_data)
                try:
                    from src.evp.evp_service import EVPService
                    EVPService.get_instance().load_map_data(map_data)
                except Exception:
                    pass

        self.data_coordinator.process_live_packet(data_packet)

        if self.selected_street_id and "street_data" in data_packet and data_packet["street_data"]:
            self._handle_street_click(self.selected_street_id)

        if self.map_widget:
            self.map_widget.update_data(data_packet)

    def _handle_panel_close(self):
        self.selected_semaphore_id = None
        self.selected_street_id = None
        if self.map_widget:
            self.map_widget.clear_all_selections()

    def _handle_mode_change(self, mode: str):
        self.current_mode = mode
        if self.selected_semaphore_id:
            self.map_widget.clear_all_selections()
            self._handle_semaphore_click(self.selected_semaphore_id)

    def _handle_semaphore_click(self, semaphore_id: Optional[str]):
        self.selected_semaphore_id = semaphore_id
        self.selected_street_id = None
        if not self.control_panel:
            return
        if not semaphore_id:
            self.control_panel.ocultar_todos_detalhes()
            return

        phase, semaphore_data = self.data_coordinator.resolve_semaphore_info(semaphore_id)
        if not semaphore_data:
            logging.warning(f"[Dashboard] Dados de painel não encontrados para {semaphore_id}")
        self.control_panel.exibir_controles_semaforo(semaphore_id, semaphore_data, phase, self.current_mode)

    def _handle_street_click(self, street_id: Optional[str]):
        self.selected_semaphore_id = None
        self.selected_street_id = street_id
        if not self.control_panel:
            return
        if street_id is None:
            self.control_panel.ocultar_todos_detalhes()
            return

        street_data_for_panel = self.data_coordinator.resolve_street_info(street_id)
        self.control_panel.exibir_info_rua(street_id, street_data_for_panel)

    def _handle_specific_command(self, semaphore_id: str, command: str):
        if self.map_widget:
            self.map_widget.set_semaphore_override_state(semaphore_id, command)

    def _handle_street_override(self, street_id: str, state: str):
        if self.map_widget:
            self.map_widget.set_street_override_state(street_id, state)

    def _handle_vehicle_click(self, vehicle_data: Dict[str, Any]):
        if hasattr(self, "vehicle_card") and self.vehicle_card:
            self.vehicle_card.display_vehicle(vehicle_data)
            if self.page:
                self.vehicle_card.update()

    def _handle_vehicle_card_close(self):
        if hasattr(self, "vehicle_card") and self.vehicle_card:
            self.vehicle_card.visible = False
            if self.page:
                self.vehicle_card.update()

    def cycle_vehicle(self):
        """Cycles through active emergency vehicles and displays their EVPVehicleCard."""
        try:
            vehicles = []
            if hasattr(self, "map_widget") and self.map_widget and hasattr(self.map_widget, "evp_overlay_manager"):
                for v_id, marker in self.map_widget.evp_overlay_manager.vehicle_markers.items():
                    if getattr(marker, "visible", True):
                        vehicles.append({
                            "vehicle_id": marker.vehicle_id,
                            "corporation": marker.corporation,
                            "latitude": marker.latitude,
                            "longitude": marker.longitude,
                            "speed_kmh": marker.speed_kmh,
                            "heading_deg": marker.heading_deg,
                            "siren_active": marker.siren_active,
                            "is_evp_triggered": marker.is_evp_triggered,
                        })

            if not vehicles:
                try:
                    from src.evp.evp_service import EVPService
                    vehicles = EVPService.get_instance().get_all_vehicles()
                except Exception:
                    pass

            if not vehicles:
                vehicles = [
                    {"vehicle_id": "SAMU-01", "corporation": "SAMU", "speed_kmh": 68.5, "heading_deg": 348.5, "siren_active": True, "is_evp_triggered": True},
                    {"vehicle_id": "BOMBEIRO-01", "corporation": "BOMBEIRO", "speed_kmh": 45.0, "heading_deg": 78.1, "siren_active": False, "is_evp_triggered": False},
                    {"vehicle_id": "POLICIA-01", "corporation": "POLICIA", "speed_kmh": 55.0, "heading_deg": 347.2, "siren_active": False, "is_evp_triggered": False},
                ]

            if not hasattr(self, "_cycle_idx"):
                self._cycle_idx = 0
            else:
                self._cycle_idx = (self._cycle_idx + 1) % len(vehicles)

            target_veh = vehicles[self._cycle_idx]
            self._handle_vehicle_click(target_veh)
        except Exception as err:
            logging.debug(f"[DashboardView] Error cycling vehicle: {err}")

