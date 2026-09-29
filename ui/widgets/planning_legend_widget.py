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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# File: ui/widgets/planning_legend_widget.py
# Author: Gabriel Moraes
# Date: 2026-08-13

import flet as ft

from ui.handlers.locale_manager import LocaleManager


class PlanningLegendWidget(ft.Container):
    """
    Widget responsável pela renderização e internacionalização da legenda do mapa de planejamento.
    """

    def __init__(self, locale_manager: LocaleManager = None):
        super().__init__(padding=ft.padding.symmetric(vertical=5))

        self.legend_title = ft.Text(weight=ft.FontWeight.BOLD)
        self.legend_tl_keep = ft.Text()
        self.legend_tl_remove = ft.Text()
        self.legend_tl_add = ft.Text()
        self.legend_junction = ft.Text()
        self.legend_street = ft.Text()

        self.content = ft.Row(
            controls=[
                self.legend_title,
                ft.Icon(ft.Icons.SQUARE, color=ft.Colors.BLUE_800, size=16),
                self.legend_tl_keep,
                ft.Icon(ft.Icons.SQUARE, color=ft.Colors.RED_700, size=16),
                self.legend_tl_remove,
                ft.Icon(ft.Icons.SQUARE, color=ft.Colors.GREEN_700, size=16),
                self.legend_tl_add,
                ft.Icon(ft.Icons.CIRCLE, color=ft.Colors.ORANGE_600, size=16),
                self.legend_junction,
                ft.Container(width=20, height=4, bgcolor=ft.Colors.BLACK, border_radius=2),
                self.legend_street,
            ],
            alignment=ft.MainAxisAlignment.CENTER,
        )

        if locale_manager:
            self.update_translations(locale_manager)
        else:
            try:
                self.update_translations(LocaleManager())
            except Exception:
                pass

    def update_translations(self, lm: LocaleManager):
        if not lm:
            return
        self.legend_title.value = lm.get_string("planning_view.legend_title", "Legenda:")
        self.legend_tl_keep.value = lm.get_string("planning_view.legend_tl_keep", "Manter")
        self.legend_tl_remove.value = lm.get_string("planning_view.legend_tl_remove", "Tirar")
        self.legend_tl_add.value = lm.get_string("planning_view.legend_tl_add", "Por")
        self.legend_junction.value = lm.get_string("planning_view.legend_junction", "Cruzamento")
        self.legend_street.value = lm.get_string("planning_view.legend_street", "Vias")
        if self.page:
            self.update()
