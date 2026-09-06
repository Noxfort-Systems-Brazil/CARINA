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

# File: ui/views/planning_view.py (Refactored to clean SOLID Layout Orchestrator)
# Author: Gabriel Moraes
# Date: December 15, 2025

import logging
import os
from datetime import datetime

import flet as ft

from ui.clients.infrastructure_client import InfrastructureClient
from ui.components.interactive_map import InteractiveMap
from ui.controllers.planning_controller import PlanningController
from ui.handlers.locale_manager import LocaleManager
from ui.widgets.planning_command_bar_widget import PlanningCommandBarWidget
from ui.widgets.planning_control_panel_widget import PlanningControlPanelWidget
from ui.widgets.planning_legend_widget import PlanningLegendWidget


class PlanningView(ft.Container):
    """
    View orquestradora da interface de planejamento urbano.
    Atua como um Composite Container responsável por compor os componentes visuais
    e repassar eventos para o Controller dedicado (PlanningController).
    """

    def __init__(
        self,
        locale_manager: LocaleManager,
        control_client=None,
        sas_result_queue=None,
        client=None,
        controller: PlanningController = None,
    ):
        super().__init__(expand=True)

        self.locale_manager = locale_manager
        self.control_client = control_client

        # Controller de negócios e estados
        self.controller = controller or PlanningController(
            locale_manager=locale_manager,
            control_client=control_client,
            sas_result_queue=sas_result_queue,
            client=client
            or InfrastructureClient(on_complete_callback=self._on_analysis_complete, sas_result_queue=sas_result_queue),
            on_complete_callback=self._on_analysis_complete,
        )

        self.file_picker = ft.FilePicker(on_result=self._on_save_result)

        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))

        # Painel lateral de controle
        self.planning_control_panel = PlanningControlPanelWidget(
            locale_manager=self.locale_manager,
            on_close_details=self._handle_panel_close,
            on_filter_change=self._handle_filter_change,
        )

        def on_node_click(tl_id):
            self._handle_node_click(tl_id)

        def on_edge_click(edge_id, edge_data):
            self._handle_edge_click(edge_id, edge_data)

        # Mapa interativo
        self.map_widget = InteractiveMap(
            project_root=project_root,
            on_node_click=on_node_click,
            on_edge_click=on_edge_click,
            on_topology_loaded=self._on_topology_loaded,
        )

        # Componente da Legenda
        self.legend_widget = PlanningLegendWidget(locale_manager=self.locale_manager)

        # Componente da Barra de Comando (Botões + Status)
        self.command_bar_widget = PlanningCommandBarWidget(
            on_analyze_click=self._load_analysis_click,
            on_save_report_click=self._save_report_click,
            locale_manager=self.locale_manager,
        )

        # Layout da área central (Mapa + Legenda)
        self.map_container = ft.Column(
            controls=[self.map_widget, self.legend_widget],
            expand=True,
            spacing=5,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

        # Layout principal (Área central + Painel Lateral)
        self.main_content = ft.Row(
            controls=[
                ft.Container(content=self.map_container, expand=True, alignment=ft.alignment.center),
                self.planning_control_panel,
            ],
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

        # Composição final da View
        self.content = ft.Column(
            controls=[self.main_content, self.command_bar_widget],
            expand=True,
            spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

    # Propriedades de compatibilidade backward para testes e chamadas diretas
    @property
    def client(self):
        return self.controller.client

    @client.setter
    def client(self, value):
        self.controller.client = value

    @property
    def last_report_content(self):
        return self.controller.last_report_content

    @last_report_content.setter
    def last_report_content(self, value):
        self.controller.last_report_content = value

    @property
    def last_scenario_dir(self):
        return self.controller.last_scenario_dir

    @last_scenario_dir.setter
    def last_scenario_dir(self, value):
        self.controller.last_scenario_dir = value

    @property
    def is_analyzing(self):
        return self.controller.is_analyzing

    @is_analyzing.setter
    def is_analyzing(self, value):
        self.controller.is_analyzing = value

    @property
    def analyze_button(self):
        return self.command_bar_widget.analyze_button

    @property
    def save_report_button(self):
        return self.command_bar_widget.save_report_button

    @property
    def status_text(self):
        return self.command_bar_widget.status_text

    @property
    def command_bar(self):
        return self.command_bar_widget

    @property
    def legend_bar(self):
        return self.legend_widget

    # Event handlers e fluxo de controle
    def _handle_node_click(self, node_id: str):
        if self.map_widget:
            self.map_widget.set_selected_node(node_id)
        if self.planning_control_panel:
            self.planning_control_panel.show_node_details(node_id)
        if self.page:
            self.page.snack_bar = ft.SnackBar(content=ft.Text(f"Semáforo/Nó selecionado: {node_id}"))
            self.page.snack_bar.open = True
            self.page.update()

    def _handle_edge_click(self, edge_id: str, edge_data: dict):
        if self.map_widget:
            self.map_widget.set_selected_edge(edge_id)
        if self.planning_control_panel:
            self.planning_control_panel.show_edge_details(edge_id, edge_data)
        if self.page:
            edge_name = edge_data.get("name", edge_id) if isinstance(edge_data, dict) else edge_id
            self.page.snack_bar = ft.SnackBar(content=ft.Text(f"Via/Rua selecionada: {edge_name}"))
            self.page.snack_bar.open = True
            self.page.update()

    def _handle_panel_close(self):
        if self.map_widget:
            self.map_widget.set_selected_node(None)
            self.map_widget.set_selected_edge(None)

    def _handle_filter_change(self, filter_key: str):
        if self.map_widget:
            self.map_widget.set_filter(filter_key)

    def did_mount(self):
        self.page.overlay.append(self.file_picker)
        self.update_translations(self.locale_manager)
        self.load_map()
        self.page.update()

    def load_map(self):
        if self.map_widget:
            self.map_widget.load_map()

    def _on_topology_loaded(self):
        if self.map_widget and self.planning_control_panel and self.map_widget.topology:
            self.planning_control_panel.set_topology(self.map_widget.topology)

        if self.is_analyzing:
            return
        self.analyze_button.disabled = False
        if self.locale_manager:
            status = self.locale_manager.get_string(
                "planning_view.status_ready", default="Topologia carregada. Pronto para análise."
            )
        else:
            status = "Topologia carregada. Pronto para análise."
        self.command_bar_widget.set_status(status, italic=True, color=None)
        self.update()

    def update_translations(self, lm: LocaleManager):
        self.legend_widget.update_translations(lm)
        self.command_bar_widget.update_translations(lm, is_analyzing=self.is_analyzing)

    def _load_analysis_click(self, e):
        # 1. Clean slate no visual e no controller
        if self.map_widget:
            self.map_widget.set_recommendations({})
        if self.planning_control_panel:
            self.planning_control_panel.hide_node_details()
            self.planning_control_panel.update_analysis_results({})

        self.analyze_button.disabled = True
        self.save_report_button.disabled = True

        if self.locale_manager:
            status = self.locale_manager.get_string(
                "planning_view.status_processing",
                default="Processando análise e gerando laudo por inteligência artificial... Por favor, aguarde.",
            )
        else:
            status = "Processando análise e gerando laudo por inteligência artificial... Por favor, aguarde."

        self.command_bar_widget.set_status(status, italic=False, color=ft.Colors.CYAN)
        self.update()

        self.map_widget.load_map()
        self.controller.trigger_analysis()

    def _on_analysis_complete(self, response: dict):
        try:
            self._process_analysis_response(response)
        except Exception as ex:
            logging.error(f"[PLANNING_VIEW] Error processing analysis response: {ex}", exc_info=True)

    def _process_analysis_response(self, response: dict):
        processed = self.controller.process_analysis_response(response)

        self.analyze_button.disabled = False

        if processed["status"] == "error":
            self.command_bar_widget.set_status(processed["message"], color=ft.Colors.RED)
            self.save_report_button.disabled = True
        else:
            recs = processed["analysis_results"]
            if recs:
                if self.map_widget:
                    self.map_widget.set_recommendations(recs)
                if self.planning_control_panel:
                    self.planning_control_panel.update_analysis_results(recs)

            self.save_report_button.disabled = not bool(self.last_report_content)

            if processed.get("significant_change") is False:
                status = self.locale_manager.get_string("planning_view.status_loaded_no_change")
                color = ft.Colors.AMBER
            else:
                status = self.locale_manager.get_string("planning_view.status_loaded_with_change")
                color = ft.Colors.GREEN

            self.command_bar_widget.set_status(status, color=color)

        if self.page:
            self.page.update()
        else:
            self.update()

    def _save_report_click(self, e):
        if not self.last_report_content:
            return

        self.file_picker.save_file(
            dialog_title=self.locale_manager.get_string("planning_view.file_picker_title"),
            file_name=f"relatorio_infraestrutura_{datetime.now().strftime('%Y%m%d')}.docx",
            allowed_extensions=["docx"],
        )

    def _on_save_result(self, e):
        if e.path and self.last_report_content:
            success, msg = self.controller.export_report(page=self.page, save_path=e.path)
            color = None if success else ft.Colors.RED
            self.command_bar_widget.set_status(msg, italic=success, color=color)
        else:
            status = self.locale_manager.get_string("planning_view.status_save_cancelled")
            self.command_bar_widget.set_status(status)
        self.update()
