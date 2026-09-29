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

# File: ui/cards/planning_summary_card.py
# Author: Gabriel Moraes
# Date: August 13, 2026

from typing import Callable, Optional

import flet as ft

from ui.formatting.planning_panel_presenter import PlanningStatsDTO
from ui.handlers.locale_manager import LocaleManager


class PlanningSummaryCard(ft.Container):
    """
    Dedicated UI Component for Network Planning Summary & Filter Chips.
    Single Responsibility: Render network-wide analytics summary and handle filter selection UI.
    """

    def __init__(
        self, on_filter_change: Optional[Callable[[str], None]] = None, locale_manager: Optional[LocaleManager] = None
    ):
        super().__init__(bgcolor=ft.Colors.BLUE_GREY_800, border_radius=8, padding=12)

        self.on_filter_change = on_filter_change
        self.lm = locale_manager
        self.active_filter: str = "ALL"

        self.stat_total_count = ft.Text("0", weight=ft.FontWeight.BOLD, size=18, color=ft.Colors.WHITE)
        self.stat_add_count = ft.Text("0", weight=ft.FontWeight.BOLD, size=14, color=ft.Colors.GREEN_400)
        self.stat_remove_count = ft.Text("0", weight=ft.FontWeight.BOLD, size=14, color=ft.Colors.RED_400)
        self.stat_keep_count = ft.Text("0", weight=ft.FontWeight.BOLD, size=14, color=ft.Colors.BLUE_400)
        self.stat_no_signal_count = ft.Text("0", weight=ft.FontWeight.BOLD, size=14, color=ft.Colors.ORANGE_400)

        self.btn_filter_all = ft.OutlinedButton(
            self._get_str("planning_summary.filter_all", "Todos"),
            on_click=lambda e: self._set_filter("ALL"),
            style=self._get_filter_style("ALL"),
        )
        self.btn_filter_add = ft.OutlinedButton(
            self._get_str("planning_summary.filter_add", "Por"),
            on_click=lambda e: self._set_filter("ADD"),
            style=self._get_filter_style("ADD"),
        )
        self.btn_filter_remove = ft.OutlinedButton(
            self._get_str("planning_summary.filter_remove", "Tirar"),
            on_click=lambda e: self._set_filter("REMOVE"),
            style=self._get_filter_style("REMOVE"),
        )
        self.btn_filter_keep = ft.OutlinedButton(
            self._get_str("planning_summary.filter_keep", "Manter"),
            on_click=lambda e: self._set_filter("KEEP"),
            style=self._get_filter_style("KEEP"),
        )

        self.lbl_title = ft.Text(
            self._get_str("planning_summary.network_summary", "Resumo da Malha Viária"),
            weight=ft.FontWeight.BOLD,
            size=13,
            color=ft.Colors.CYAN_200,
        )
        self.lbl_total = ft.Text(
            self._get_str("planning_summary.total_analyzed", "Total Analisado:"), size=12, color=ft.Colors.WHITE70
        )
        self.lbl_add = ft.Text(self._get_str("planning_summary.add", "Adicionar:"), size=11, color=ft.Colors.WHITE70)
        self.lbl_remove = ft.Text(
            self._get_str("planning_summary.remove", "Remover:"), size=11, color=ft.Colors.WHITE70
        )
        self.lbl_keep = ft.Text(self._get_str("planning_summary.keep", "Manter:"), size=11, color=ft.Colors.WHITE70)
        self.lbl_uncontrolled = ft.Text(
            self._get_str("planning_summary.uncontrolled", "Não Sinalizado:"), size=11, color=ft.Colors.WHITE70
        )
        self.lbl_filter = ft.Text(
            self._get_str("planning_summary.filter_title", "Filtrar Recomendações:"),
            size=11,
            color=ft.Colors.WHITE60,
            italic=True,
        )

        self.content = ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.ANALYTICS_ROUNDED, color=ft.Colors.CYAN_400, size=20),
                        self.lbl_title,
                    ],
                    alignment=ft.MainAxisAlignment.START,
                ),
                ft.Divider(height=1, color=ft.Colors.WHITE10),
                ft.Row(
                    controls=[self.lbl_total, self.stat_total_count],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Row(
                    controls=[
                        ft.Row(
                            [
                                ft.Icon(ft.Icons.ADD_CIRCLE, color=ft.Colors.GREEN_400, size=14),
                                self.lbl_add,
                            ]
                        ),
                        self.stat_add_count,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Row(
                    controls=[
                        ft.Row(
                            [
                                ft.Icon(ft.Icons.REMOVE_CIRCLE, color=ft.Colors.RED_400, size=14),
                                self.lbl_remove,
                            ]
                        ),
                        self.stat_remove_count,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Row(
                    controls=[
                        ft.Row(
                            [
                                ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.BLUE_400, size=14),
                                self.lbl_keep,
                            ]
                        ),
                        self.stat_keep_count,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Row(
                    controls=[
                        ft.Row(
                            [
                                ft.Icon(ft.Icons.WARNING_ROUNDED, color=ft.Colors.ORANGE_400, size=14),
                                self.lbl_uncontrolled,
                            ]
                        ),
                        self.stat_no_signal_count,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Container(height=5),
                self.lbl_filter,
                ft.Row(
                    controls=[self.btn_filter_all, self.btn_filter_add, self.btn_filter_remove, self.btn_filter_keep],
                    spacing=4,
                    alignment=ft.MainAxisAlignment.START,
                ),
            ],
            spacing=6,
        )

    def _get_str(self, key: str, default: str) -> str:
        if self.lm:
            return self.lm.get_string(key, default=default)
        return default

    def update_translations(self, lm: LocaleManager) -> None:
        self.lm = lm
        self.lbl_title.value = self._get_str("planning_summary.network_summary", "Resumo da Malha Viária")
        self.lbl_total.value = self._get_str("planning_summary.total_analyzed", "Total Analisado:")
        self.lbl_add.value = self._get_str("planning_summary.add", "Adicionar:")
        self.lbl_remove.value = self._get_str("planning_summary.remove", "Remover:")
        self.lbl_keep.value = self._get_str("planning_summary.keep", "Manter:")
        self.lbl_uncontrolled.value = self._get_str("planning_summary.uncontrolled", "Não Sinalizado:")
        self.lbl_filter.value = self._get_str("planning_summary.filter_title", "Filtrar Recomendações:")

        self.btn_filter_all.text = self._get_str("planning_summary.filter_all", "Todos")
        self.btn_filter_add.text = self._get_str("planning_summary.filter_add", "Por")
        self.btn_filter_remove.text = self._get_str("planning_summary.filter_remove", "Tirar")
        self.btn_filter_keep.text = self._get_str("planning_summary.filter_keep", "Manter")

        if self.page:
            self.update()

    def _get_filter_style(self, filter_key: str) -> ft.ButtonStyle:
        is_active = self.active_filter == filter_key
        bg = ft.Colors.CYAN_700 if is_active else ft.Colors.TRANSPARENT
        fg = ft.Colors.WHITE if is_active else ft.Colors.WHITE70
        return ft.ButtonStyle(
            bgcolor=bg,
            color=fg,
            overlay_color=ft.Colors.TRANSPARENT,
            shadow_color=ft.Colors.TRANSPARENT,
            elevation=0,
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
            shape=ft.RoundedRectangleBorder(radius=4),
        )

    def _set_filter(self, filter_key: str):
        self.active_filter = filter_key
        self.btn_filter_all.style = self._get_filter_style("ALL")
        self.btn_filter_add.style = self._get_filter_style("ADD")
        self.btn_filter_remove.style = self._get_filter_style("REMOVE")
        self.btn_filter_keep.style = self._get_filter_style("KEEP")

        if self.on_filter_change:
            self.on_filter_change(filter_key)
        if self.page:
            self.update()

    def update_stats(self, stats: PlanningStatsDTO):
        """Updates summary labels from a structured PlanningStatsDTO."""
        self.stat_total_count.value = str(stats.total)
        self.stat_add_count.value = str(stats.add_count)
        self.stat_remove_count.value = str(stats.remove_count)
        self.stat_keep_count.value = str(stats.keep_count)
        self.stat_no_signal_count.value = str(stats.no_signal_count)

        if self.page:
            self.update()
