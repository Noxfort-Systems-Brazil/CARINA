# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Emergency Vehicle Preemption (EVP) Settings Module Handler.
Coordinates the lifecycle of Flet visual components (dialogs, pickers, and tables)
and delegates data buffer transactional management to EVPStagingBuffer (SRP / Clean Architecture).
"""

import logging
from typing import Any, Dict, List, Optional, Set, Tuple
import flet as ft

from src.evp.evp_config_repo import EVPConfigRepository
from src.evp.evp_models import RegisteredVehicle
from src.evp.evp_service import EVPService
from ui.handlers.evp_staging_buffer import EVPStagingBuffer

logger = logging.getLogger(__name__)


class EVPSettingsHandler:
    """
    Orchestrates the visual interface for the EVP fleet connection card in the Settings modal.
    Delegates in-memory transactional manipulation to EVPStagingBuffer.
    """

    def __init__(
        self,
        evp_service: Optional[EVPService] = None,
        settings_client=None,
        locale_manager=None,
    ):
        self.evp_service = evp_service or EVPService.get_instance()
        self.settings_client = settings_client
        self.locale_manager = locale_manager
        self.page: Optional[ft.Page] = None
        self.evp_card = None

        self.import_picker = ft.FilePicker(on_result=self._on_import_result)
        self.export_picker = ft.FilePicker(on_result=self._on_export_result)
        self.buffer = EVPStagingBuffer()

        self._capture_initial_state()

    @property
    def _initial_saved_fleet(self) -> Dict[str, RegisteredVehicle]:
        return self.buffer._initial_saved_fleet

    @_initial_saved_fleet.setter
    def _initial_saved_fleet(self, val: Dict[str, RegisteredVehicle]):
        self.buffer._initial_saved_fleet = val

    @property
    def _staged_fleet(self) -> Dict[str, RegisteredVehicle]:
        return self.buffer._staged_fleet

    @_staged_fleet.setter
    def _staged_fleet(self, val: Dict[str, RegisteredVehicle]):
        self.buffer._staged_fleet = val

    @property
    def _staged_removals(self) -> Set[str]:
        return self.buffer._staged_removals

    @_staged_removals.setter
    def _staged_removals(self, val: Set[str]):
        self.buffer._staged_removals = val

    def _capture_initial_state(self) -> None:
        """Loads and captures persisted fleet as initial reference baseline for the buffer."""
        loaded = {}
        try:
            loaded = EVPConfigRepository.load_all_vehicles_db(locale_manager=self.locale_manager)
        except Exception as e:
            logger.debug(f"[EVPSettingsHandler] Erro ao carregar frota do banco: {e}")

        if not loaded and hasattr(self.evp_service, "get_registered_fleet"):
            fleet_list = self.evp_service.get_registered_fleet()
            for item in fleet_list:
                if isinstance(item, dict):
                    v = RegisteredVehicle.from_dict(item)
                    loaded[v.vehicle_id] = v
                elif hasattr(item, "vehicle_id"):
                    loaded[item.vehicle_id] = item
        elif not loaded and hasattr(self.evp_service, "_registered_fleet"):
            loaded = {k: v for k, v in self.evp_service._registered_fleet.items()}
        elif not loaded and hasattr(self.evp_service, "fleet_manager") and hasattr(self.evp_service.fleet_manager, "_fleet"):
            loaded = {k: v for k, v in self.evp_service.fleet_manager._fleet.items()}

        self.buffer.capture_initial_state(loaded)

    def mount(self, page: ft.Page, evp_card) -> None:
        """Binds the visual card and registers FilePickers in the page overlay."""
        self.page = page
        self.evp_card = evp_card
        if self.evp_card:
            self.evp_card.handler = self
        if self.page:
            if self.import_picker not in self.page.overlay:
                self.page.overlay.append(self.import_picker)
            if self.export_picker not in self.page.overlay:
                self.page.overlay.append(self.export_picker)

        self._capture_initial_state()
        self.refresh_ui()

    def refresh_ui(self) -> None:
        """Updates the table with RAM-staged state combined with active telemetry."""
        if not self.evp_card:
            return

        active_vehicles = getattr(self.evp_service, "_vehicles", {})
        fleet_dtos = self.buffer.build_fleet_dtos(active_vehicles)

        if hasattr(self.evp_card, "fleet_table") and hasattr(self.evp_card.fleet_table, "set_vehicles"):
            self.evp_card.fleet_table.set_vehicles(fleet_dtos)
        elif hasattr(self.evp_card, "update_fleet_list"):
            self.evp_card.update_fleet_list(fleet_dtos)

        if self.page:
            self.page.update()

    def on_register_vehicle(self, data: Any) -> Tuple[bool, str]:
        """Registers a vehicle in the in-memory transactional buffer."""
        success, message = self.buffer.stage_vehicle(data)
        if success:
            self.refresh_ui()
        return success, message

    def on_remove_vehicle(self, vehicle_id: str) -> bool:
        """Removes the vehicle from the in-memory staging buffer."""
        found = self.buffer.stage_removal(vehicle_id)
        self.refresh_ui()
        return found

    def on_import_click(self, e) -> None:
        """Opens file picker to import fleet CSV."""
        dialog_title = "Selecionar Planilha CSV de Frota EVP"
        if self.locale_manager:
            dialog_title = self.locale_manager.get_string(
                "settings_view.evp_card.select_dialog_title", default=dialog_title
            )
        self.import_picker.pick_files(dialog_title=dialog_title, allowed_extensions=["csv"])

    def _on_import_result(self, e: ft.FilePickerResultEvent) -> None:
        """Processes CSV sheet without saving to database immediately (save_to_db=False)."""
        if e.files and len(e.files) > 0:
            filepath = e.files[0].path
            imported_vehicles = EVPConfigRepository.import_csv_config(filepath)
            for v in imported_vehicles:
                self.buffer.stage_vehicle(v)

            self.refresh_ui()

            if self.page:
                msg = f"✅ {len(imported_vehicles)} viaturas importadas para staging com sucesso!"
                self.page.snack_bar = ft.SnackBar(content=ft.Text(msg))
                self.page.snack_bar.open = True
                self.page.update()

    def on_export_click(self, e) -> None:
        """Opens file picker to export fleet CSV template."""
        dialog_title = "Salvar Modelo CSV de Frota"
        if self.locale_manager:
            dialog_title = self.locale_manager.get_string(
                "settings_view.evp_card.save_dialog_title", default=dialog_title
            )
        self.export_picker.save_file(
            dialog_title=dialog_title,
            file_name="frota_evp_template.csv",
            allowed_extensions=["csv"],
        )

    def _on_export_result(self, e: ft.FilePickerResultEvent) -> None:
        """Writes CSV file with staged vehicles or example template."""
        if e.path:
            save_path = e.path if e.path.lower().endswith(".csv") else f"{e.path}.csv"
            success = EVPConfigRepository.export_csv_template(save_path, self.buffer.staged_fleet)
            if self.page:
                msg = "✅ Modelo CSV exportado com sucesso!" if success else "❌ Erro ao exportar modelo CSV."
                self.page.snack_bar = ft.SnackBar(content=ft.Text(msg))
                self.page.snack_bar.open = True
                self.page.update()

    def has_unsaved_changes(self) -> bool:
        """Determines if there are pending unsaved fleet changes."""
        return self.buffer.has_unsaved_changes()

    def save_changes(self) -> bool:
        """
        Persists changes to database and synchronizes preemption service.
        Called by SettingsView main 'Save' button (Hardware parity).
        """
        # 1. Delete removed vehicles from database and service
        for v_id in list(self.buffer.staged_removals):
            EVPConfigRepository.remove_vehicle_db(v_id, locale_manager=self.locale_manager)
            self.evp_service.unregister_fleet_vehicle(v_id)

        # 2. Persist new or updated vehicles to database and service
        for v in self.buffer.staged_fleet.values():
            if v.vehicle_id not in self.buffer.staged_removals:
                EVPConfigRepository.save_vehicle_db(v, locale_manager=self.locale_manager)
                self.evp_service.register_fleet_vehicle(v)

        # 3. Notify backend via settings_client if applicable
        if self.settings_client and hasattr(self.settings_client, "send_command"):
            try:
                self.settings_client.send_command("set_evp_fleet", {"action": "sync"})
            except Exception:
                pass

        # 4. Update initial snapshot and clear removals
        self.buffer.commit_changes()
        self.refresh_ui()
        logger.info("[EVPSettingsHandler] Alterações da frota EVP salvas com sucesso no banco de dados.")
        return True

    def discard_changes(self) -> None:
        """Discards uncommitted RAM modifications, restoring database-persisted state."""
        self.buffer.discard_changes()
        self.refresh_ui()
        logger.info("[EVPSettingsHandler] Alterações em RAM da frota EVP descartadas.")
