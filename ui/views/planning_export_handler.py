# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: ui/views/planning_export_handler.py
# Author: Gabriel Moraes
# Date: September 2026

from datetime import datetime
from typing import Any, Callable, Optional

import flet as ft

from ui.handlers.locale_manager import LocaleManager


class PlanningExportHandler:
    """
    Handles file dialogs, file picker events, and export triggers for planning reports.
    Follows Single Responsibility Principle (SRP).
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
