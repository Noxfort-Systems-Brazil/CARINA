# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# File: ui/widgets/planning_command_bar_widget.py
# Author: Gabriel Moraes
# Date: 2026-08-13

import flet as ft

from ui.handlers.locale_manager import LocaleManager


class PlanningCommandBarWidget(ft.Container):
    """
    Widget responsável pela barra inferior de comandos de planejamento (botões de ação e indicador de status).
    """

    def __init__(self, on_analyze_click=None, on_save_report_click=None, locale_manager: LocaleManager = None):
        super().__init__(
            height=60,
            padding=ft.padding.symmetric(horizontal=20),
            border_radius=ft.border_radius.only(top_left=10, top_right=10),
            bgcolor=ft.Colors.WHITE10,
        )

        self.analyze_button = ft.ElevatedButton("Carregar Análise", disabled=True, on_click=on_analyze_click)
        self.save_report_button = ft.ElevatedButton(
            "Gerar Relatório", icon=ft.Icons.SAVE_ALT_ROUNDED, on_click=on_save_report_click, disabled=True
        )
        self.status_text = ft.Text("Aguardando carregamento da topologia do mapa...", italic=True)

        self.content = ft.Row(
            controls=[
                self.analyze_button,
                ft.Container(expand=True),
                self.status_text,
                ft.Container(expand=True),
                self.save_report_button,
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        if locale_manager:
            self.update_translations(locale_manager)

    def set_status(self, text: str, italic: bool = False, color=None):
        self.status_text.value = text
        self.status_text.italic = italic
        self.status_text.color = color

    def update_translations(self, lm: LocaleManager, is_analyzing: bool = False):
        if not lm:
            return
        self.analyze_button.text = lm.get_string("planning_view.analyze_button")
        self.analyze_button.tooltip = lm.get_string("planning_view.analyze_tooltip")
        self.save_report_button.text = lm.get_string("planning_view.generate_report_button")
        if not is_analyzing and not self.analyze_button.disabled:
            self.status_text.value = lm.get_string("planning_view.status_ready")
