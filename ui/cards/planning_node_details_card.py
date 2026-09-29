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

# File: ui/cards/planning_node_details_card.py
# Author: Gabriel Moraes
# Date: August 13, 2026

from typing import Callable, Optional

import flet as ft

from ui.formatting.planning_panel_presenter import NodeDetailsDTO
from ui.handlers.locale_manager import LocaleManager


class PlanningNodeDetailsCard(ft.Container):
    """
    Dedicated UI Component for Selected Junction Details & AI Rationale.
    Single Responsibility: Render individual junction engineering metrics and technical justification.
    """

    def __init__(self, on_close: Optional[Callable[[], None]] = None, locale_manager: Optional[LocaleManager] = None):
        super().__init__(bgcolor=ft.Colors.BLUE_GREY_800, border_radius=8, padding=12, visible=False)

        self.on_close = on_close
        self.lm = locale_manager
        self.current_node_id: Optional[str] = None

        self.node_title = ft.Text(
            self._get_str("planning_details.node_label", "Nó:"),
            weight=ft.FontWeight.BOLD,
            size=14,
            color=ft.Colors.WHITE,
        )
        self.rec_badge = ft.Container(
            content=ft.Text(
                self._get_str("planning_details.no_selection", "SEM SELEÇÃO"),
                weight=ft.FontWeight.BOLD,
                size=11,
                color=ft.Colors.WHITE,
            ),
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
            border_radius=4,
            bgcolor=ft.Colors.GREY_700,
        )
        self.btn_close_details = ft.IconButton(
            icon=ft.Icons.CLOSE,
            icon_size=16,
            tooltip=self._get_str("planning_details.close_tooltip", "Fechar detalhes"),
            on_click=self._handle_close_click,
        )

        self.val_saturation = ft.Text("-", weight=ft.FontWeight.BOLD, size=12, color=ft.Colors.WHITE)
        self.val_delay = ft.Text("-", weight=ft.FontWeight.BOLD, size=12, color=ft.Colors.WHITE)
        self.val_flow = ft.Text("-", weight=ft.FontWeight.BOLD, size=12, color=ft.Colors.WHITE)
        self.val_warrant = ft.Text("-", weight=ft.FontWeight.BOLD, size=12, color=ft.Colors.WHITE)

        self.lbl_metrics = ft.Text(
            self._get_str("planning_details.metrics_title", "Métricas da Interseção:"),
            weight=ft.FontWeight.BOLD,
            size=11,
            color=ft.Colors.CYAN_200,
        )
        self.lbl_saturation = ft.Text(
            self._get_str("planning_details.saturation_rate", "Taxa de Saturação:"), size=11, color=ft.Colors.WHITE70
        )
        self.lbl_delay = ft.Text(
            self._get_str("planning_details.avg_delay", "Atraso Médio (s):"), size=11, color=ft.Colors.WHITE70
        )
        self.lbl_flow = ft.Text(
            self._get_str("planning_details.estimated_flow", "Fluxo Estimado (v/h):"), size=11, color=ft.Colors.WHITE70
        )
        self.lbl_warrant = ft.Text(
            self._get_str("planning_details.contran_warrant", "Warrant CONTRAN:"), size=11, color=ft.Colors.WHITE70
        )
        self.lbl_opinion = ft.Text(
            self._get_str("planning_details.technical_opinion", "Parecer Técnico SAS:"),
            weight=ft.FontWeight.BOLD,
            size=11,
            color=ft.Colors.CYAN_200,
        )

        self.text_justification = ft.Text(
            self._get_str(
                "planning_details.click_to_inspect",
                "Clique em um semáforo ou cruzamento no mapa para inspecionar a recomendação da IA e o laudo de engenharia.",
            ),
            size=11,
            color=ft.Colors.WHITE70,
        )

        self.content = ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Row(
                            [ft.Icon(ft.Icons.LOCATION_ON, color=ft.Colors.AMBER_400, size=18), self.node_title],
                            spacing=4,
                        ),
                        self.btn_close_details,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                self.rec_badge,
                ft.Divider(height=1, color=ft.Colors.WHITE10),
                self.lbl_metrics,
                ft.Row(
                    controls=[self.lbl_saturation, self.val_saturation],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Row(
                    controls=[self.lbl_delay, self.val_delay],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Row(
                    controls=[self.lbl_flow, self.val_flow],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Row(
                    controls=[self.lbl_warrant, self.val_warrant],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Container(height=5),
                self.lbl_opinion,
                ft.Container(
                    content=ft.Column(
                        controls=[self.text_justification],
                        scroll=ft.ScrollMode.AUTO,
                    ),
                    height=140,
                    bgcolor=ft.Colors.BLACK26,
                    padding=8,
                    border_radius=4,
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
        prefix = self._get_str("planning_details.node_label", "Nó:")
        if self.current_node_id:
            self.node_title.value = f"{prefix} {self.current_node_id}"
        else:
            self.node_title.value = prefix

        self.btn_close_details.tooltip = self._get_str("planning_details.close_tooltip", "Fechar detalhes")
        self.lbl_metrics.value = self._get_str("planning_details.metrics_title", "Métricas da Interseção:")
        self.lbl_saturation.value = self._get_str("planning_details.saturation_rate", "Taxa de Saturação:")
        self.lbl_delay.value = self._get_str("planning_details.avg_delay", "Atraso Médio (s):")
        self.lbl_flow.value = self._get_str("planning_details.estimated_flow", "Fluxo Estimado (v/h):")
        self.lbl_warrant.value = self._get_str("planning_details.contran_warrant", "Warrant CONTRAN:")
        self.lbl_opinion.value = self._get_str("planning_details.technical_opinion", "Parecer Técnico SAS:")

        if not self.current_node_id:
            self.rec_badge.content.value = self._get_str("planning_details.no_selection", "SEM SELEÇÃO")
            self.text_justification.value = self._get_str(
                "planning_details.click_to_inspect",
                "Clique em um semáforo ou cruzamento no mapa para inspecionar a recomendação da IA e o laudo de engenharia.",
            )

        if self.page:
            self.update()

    def show_node(self, details: NodeDetailsDTO):
        """Populates UI elements from a formatted NodeDetailsDTO and makes card visible."""
        self.current_node_id = details.node_id
        prefix = self._get_str("planning_details.node_label", "Nó:")
        self.node_title.value = f"{prefix} {details.node_id}"
        self.rec_badge.content.value = details.rec_label
        self.rec_badge.bgcolor = details.rec_bg_color
        self.val_saturation.value = details.saturation_str
        self.val_delay.value = details.delay_str
        self.val_flow.value = details.flow_str
        self.val_warrant.value = details.warrant_str
        self.text_justification.value = details.justification_str

        self.visible = True
        if self.page:
            self.update()

    def hide_card(self):
        """Hides the node details card."""
        self.current_node_id = None
        self.visible = False
        if self.page:
            self.update()

    def _handle_close_click(self, e):
        self.hide_card()
        if self.on_close:
            self.on_close()
