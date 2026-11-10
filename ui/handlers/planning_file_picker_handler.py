# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import Any, Callable, Optional

import flet as ft

from ui.handlers.locale_manager import LocaleManager


class PlanningFilePickerHandler:
    """
    Specialized handler for FilePicker dialogs and events to save planning reports.
    Strictly follows the Single Responsibility Principle (SRP).
    """

    @staticmethod
    def request_save_file(file_picker: ft.FilePicker, locale_manager: LocaleManager) -> None:
        """Opens native OS save file dialog for exporting DOCX report."""
        timestamp = datetime.now().strftime("%Y%m%d")
        title = locale_manager.get_string("planning_view.file_picker_title", default="Salvar Laudo de Planejamento")
        file_picker.save_file(
            dialog_title=title,
            file_name=f"relatorio_infraestrutura_{timestamp}.docx",
            allowed_extensions=["docx"],
        )

    @staticmethod
    def on_save_result(
        e: ft.FilePickerResultEvent,
        last_report_content: Optional[str],
        controller: Any,
        page: Optional[ft.Page],
        command_bar_widget: Any,
        locale_manager: LocaleManager,
        update_callback: Callable[[], None],
    ) -> None:
        """Processes user file path selection from FilePicker and exports document."""
        if e.path and last_report_content:
            success, msg = controller.export_report(page=page, save_path=e.path)
            color = None if success else ft.Colors.RED
            command_bar_widget.set_status(msg, italic=success, color=color)
        else:
            status = locale_manager.get_string(
                "planning_view.status_save_cancelled", default="Operação de salvamento cancelada."
            )
            command_bar_widget.set_status(status)

        update_callback()
