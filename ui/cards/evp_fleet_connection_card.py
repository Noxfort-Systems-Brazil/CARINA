# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Emergency Vehicle Preemption (EVP) Fleet Connection and Management Card.
Acts as orchestrating View, delegating the table to EVPFleetTable,
the modal to EVPVehicleDialog, the legend to EVPContranLegend,
and operations to EVPFleetController.
"""

import logging
from typing import Any, Dict, List, Optional
import flet as ft

from ui.components.evp_contran_legend import EVPContranLegend
from ui.components.evp_fleet_table import EVPFleetTable
from ui.controllers.evp_fleet_controller import EVPFleetController
from ui.dialogs.evp_vehicle_dialog import EVPVehicleDialog

logger = logging.getLogger(__name__)


class EVPFleetConnectionCard(ft.Card):
    """
    Fleet Connections Card in the System Settings modal.
    """

    def __init__(
        self,
        locale_manager: Any = None,
        controller: Optional[EVPFleetController] = None,
        dialog: Optional[EVPVehicleDialog] = None,
        handler: Optional[Any] = None,
    ):
        super().__init__()
        self.elevation = 2
        self.expand = True
        self.locale_manager = locale_manager
        self.handler = handler
        self.controller = controller or EVPFleetController()
        self.dialog = dialog or EVPVehicleDialog(on_save=self._on_vehicle_dialog_save)
        self.fleet_table = EVPFleetTable(on_delete=self._remove_vehicle)

        self.import_picker = ft.FilePicker(on_result=self._on_import_result)
        self.export_picker = ft.FilePicker(on_result=self._on_export_result)

        self.title_text = ft.Text("Conexões da Frota de Emergência", size=18, weight=ft.FontWeight.BOLD)

        self.btn_add = ft.ElevatedButton(
            "Cadastrar Viatura",
            icon=ft.Icons.ADD_ROUNDED,
            bgcolor=ft.Colors.BLUE_700,
            color=ft.Colors.WHITE,
            on_click=lambda _: self.dialog.open(),
        )
        self.btn_export = ft.ElevatedButton(
            "Baixar Modelo CSV",
            icon=ft.Icons.DOWNLOAD_ROUNDED,
            on_click=self._handle_export_click,
        )
        self.btn_import = ft.ElevatedButton(
            "Importar CSV",
            icon=ft.Icons.UPLOAD_ROUNDED,
            bgcolor=ft.Colors.TEAL_700,
            color=ft.Colors.WHITE,
            on_click=self._handle_import_click,
        )
        self.btn_refresh = ft.IconButton(
            icon=ft.Icons.REFRESH_ROUNDED,
            tooltip="Atualizar Status",
            on_click=lambda _: self.refresh_fleet(),
        )

        self._build_layout()

        try:
            from src.evp.evp_notifier import EVPNotifier
            EVPNotifier.get_instance().register_listener(lambda _: self.refresh_fleet())
        except Exception:
            pass

    def mount(self, page: ft.Page):
        """Registers FilePickers and Dialogs in page overlay."""
        self.page = page
        if self.page:
            if self.import_picker not in self.page.overlay:
                self.page.overlay.append(self.import_picker)
            if self.export_picker not in self.page.overlay:
                self.page.overlay.append(self.export_picker)
            self.dialog.mount(self.page)
        if self.handler and hasattr(self.handler, "mount") and getattr(self.handler, "page", None) != self.page:
            self.handler.mount(page, self)
        else:
            self.refresh_fleet()

    def _build_layout(self):
        header_row = ft.Row(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.ROUTER_ROUNDED, color=ft.Colors.TEAL_400),
                        self.title_text,
                    ],
                    alignment=ft.MainAxisAlignment.START,
                ),
                ft.Row(
                    controls=[
                        self.btn_add,
                        self.btn_import,
                        self.btn_export,
                        self.btn_refresh,
                    ],
                    alignment=ft.MainAxisAlignment.END,
                    spacing=8,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            wrap=True,
        )

        self.content = ft.Container(
            padding=16,
            expand=True,
            content=ft.Column(
                expand=True,
                spacing=12,
                controls=[
                    header_row,
                    ft.Text(
                        "Cadastre manualmente ou importe via arquivo CSV as viaturas autorizadas para preempção semafórica segura. "
                        "A CARINA detecta automaticamente a aproximação viária pelo mapa sem necessidade de parametrização manual de quadra.",
                        size=12,
                        color=ft.Colors.GREY_400,
                    ),
                    EVPContranLegend(),
                    ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                    self.fleet_table,
                ],
            ),
        )

    def _build_contran_legend(self) -> ft.Control:
        return EVPContranLegend()

    def _on_vehicle_dialog_save(self, data: Dict[str, Any]):
        if self.handler and hasattr(self.handler, "on_register_vehicle"):
            success, msg = self.handler.on_register_vehicle(data)
        else:
            success, msg = self.controller.register_vehicle(data)
            if success:
                self.save_changes()
            self.refresh_fleet()
        if self.page:
            prefix = "✅ " if success else "❌ "
            self.page.snack_bar = ft.SnackBar(content=ft.Text(f"{prefix}{msg}"))
            self.page.snack_bar.open = True
            self.page.update()

    def _remove_vehicle(self, vehicle_id: str):
        if self.handler and hasattr(self.handler, "on_remove_vehicle"):
            success = self.handler.on_remove_vehicle(vehicle_id)
        else:
            success = self.controller.unregister_vehicle(vehicle_id)
            if success:
                self.save_changes()
            self.refresh_fleet()
        if self.page:
            msg = f"🗑️ Viatura {vehicle_id} removida com sucesso!" if success else f"⚠️ Viatura {vehicle_id} não encontrada."
            self.page.snack_bar = ft.SnackBar(content=ft.Text(msg))
            self.page.snack_bar.open = True
            self.page.update()

    def _handle_import_click(self, e):
        if self.handler and hasattr(self.handler, "on_import_click"):
            self.handler.on_import_click(e)
            return
        self.import_picker.pick_files(
            dialog_title="Selecionar Planilha CSV de Frota EVP",
            allowed_extensions=["csv"],
        )

    def _on_import_result(self, e: ft.FilePickerResultEvent):
        if e.files and len(e.files) > 0:
            filepath = e.files[0].path
            success, total = self.controller.import_csv(filepath)
            if success > 0:
                self.save_changes()
            self.refresh_fleet()

            if self.page:
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text(f"✅ {success} de {total} viaturas importadas com sucesso!")
                )
                self.page.snack_bar.open = True
                self.page.update()

    def _handle_export_click(self, e):
        if self.handler and hasattr(self.handler, "on_export_click"):
            self.handler.on_export_click(e)
            return
        self.export_picker.save_file(
            dialog_title="Salvar Modelo CSV de Frota",
            file_name="frota_evp_template.csv",
            allowed_extensions=["csv"],
        )

    def _on_export_result(self, e: ft.FilePickerResultEvent):
        if e.path:
            save_path = e.path if e.path.lower().endswith(".csv") else f"{e.path}.csv"
            success = self.controller.export_csv(save_path)
            if self.page:
                msg = "✅ Modelo CSV exportado com sucesso!" if success else "❌ Erro ao exportar modelo CSV."
                self.page.snack_bar = ft.SnackBar(content=ft.Text(msg))
                self.page.snack_bar.open = True
                self.page.update()

    def refresh_fleet(self):
        if self.handler and hasattr(self.handler, "refresh_ui"):
            self.handler.refresh_ui()
            return
        vehicles = self.controller.get_fleet()
        self.fleet_table.set_vehicles(vehicles)
        if self.page:
            self.update()

    def has_unsaved_changes(self) -> bool:
        if self.handler and hasattr(self.handler, "has_unsaved_changes"):
            return self.handler.has_unsaved_changes()
        return self.controller.has_unsaved_changes()

    def save_changes(self) -> bool:
        if self.handler and hasattr(self.handler, "save_changes"):
            self.handler.save_changes()
            return True
        success = self.controller.save_changes()
        self.refresh_fleet()
        return success

    def discard_changes(self) -> None:
        if self.handler and hasattr(self.handler, "discard_changes"):
            self.handler.discard_changes()
            return
        self.controller.discard_changes()
        self.refresh_fleet()
