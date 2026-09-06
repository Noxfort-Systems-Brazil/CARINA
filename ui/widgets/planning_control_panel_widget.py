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

# File: ui/widgets/planning_control_panel_widget.py
# Author: Gabriel Moraes
# Date: August 13, 2026

from typing import Any, Callable, Dict, Optional

import flet as ft

from ui.cards.planning_node_details_card import PlanningNodeDetailsCard
from ui.cards.planning_summary_card import PlanningSummaryCard
from ui.formatting.planning_panel_presenter import PlanningPanelPresenter
from ui.handlers.locale_manager import LocaleManager


class PlanningControlPanelWidget(ft.Container):
    """
    Pure UI Orchestrator Container for the Planning and Optimization View.
    Solid Architecture Compliance:
    - SRP: Delegates layout rendering to specialized cards and data logic to PlanningPanelPresenter.
    - OCP: Extensible via Presenter DTO mappings without modifying widget layout logic.
    - DIP: Relies on abstractions and callbacks for user interaction events.
    """

    def __init__(
        self,
        locale_manager: LocaleManager,
        on_close_details: Optional[Callable[[], None]] = None,
        on_filter_change: Optional[Callable[[str], None]] = None,
    ):
        super().__init__(width=340, bgcolor=ft.Colors.BLUE_GREY_900, border_radius=10, padding=15)

        self.locale_manager = locale_manager
        self.on_close_details = on_close_details
        self.on_filter_change = on_filter_change

        self.analysis_results: Dict[str, Any] = {}
        self.selected_node_id: Optional[str] = None

        # --- Header ---
        self.header_title = ft.Text("Planejamento Tático", weight=ft.FontWeight.BOLD, size=16, color=ft.Colors.WHITE)
        self.header_subtitle = ft.Text("Diagnóstico & Recomendador IA", size=11, color=ft.Colors.WHITE70, italic=True)

        # --- Sub-Cards Composition ---
        self.summary_card = PlanningSummaryCard(on_filter_change=self.on_filter_change)
        self.details_card = PlanningNodeDetailsCard(on_close=self._handle_close_click)
        self.topology = None

        self.content = ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.MAP_ROUNDED, color=ft.Colors.CYAN_400, size=24),
                        ft.Column([self.header_title, self.header_subtitle], spacing=1),
                    ],
                    spacing=8,
                ),
                ft.Divider(height=1, color=ft.Colors.WHITE24),
                self.summary_card,
                self.details_card,
            ],
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

    def set_topology(self, topology: Dict[str, Any]):
        """Sets the network topology reference for physical engineering calculations."""
        self.topology = topology

    def update_analysis_results(self, recs: Dict[str, Any]):
        """Orchestrates network statistics calculation and updates the summary card."""
        self.analysis_results = recs or {}

        stats = PlanningPanelPresenter.compute_statistics(self.analysis_results)
        self.summary_card.update_stats(stats)

        if self.selected_node_id and self.selected_node_id in self.analysis_results:
            self.show_node_details(self.selected_node_id, self.analysis_results[self.selected_node_id])

    def show_node_details(self, node_id: str, node_data: Optional[Dict[str, Any]] = None):
        """Orchestrates node formatting via presenter and updates the details card."""
        self.selected_node_id = node_id

        if node_data is None and node_id in self.analysis_results:
            node_data = self.analysis_results[node_id]

        details_dto = PlanningPanelPresenter.format_node_details(
            node_id=node_id, node_data=node_data, topology=self.topology
        )
        self.details_card.show_node(details_dto)

    def show_edge_details(self, edge_id: str, edge_data: Optional[Dict[str, Any]] = None):
        """Orchestrates street/via formatting via presenter and updates the details card."""
        self.selected_node_id = None
        details_dto = PlanningPanelPresenter.format_edge_details(edge_id, edge_data)
        self.details_card.show_node(details_dto)

    def hide_node_details(self):
        """Orchestrates hiding the node/edge details card."""
        self.selected_node_id = None
        self.details_card.hide_card()

    def _handle_close_click(self):
        self.hide_node_details()
        if self.on_close_details:
            self.on_close_details()
