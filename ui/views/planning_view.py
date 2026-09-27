# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: ui/views/planning_view.py
# Author: Gabriel Moraes
# Date: September 2026

import logging
import os
from typing import Any, Optional

import flet as ft

from ui.clients.infrastructure_client import InfrastructureClient
from ui.components.interactive_map import InteractiveMap
from ui.controllers.planning_controller import PlanningController
from ui.handlers.locale_manager import LocaleManager
from ui.views.planning_export_handler import PlanningExportHandler
from ui.widgets.planning_command_bar_widget import PlanningCommandBarWidget
from ui.widgets.planning_control_panel_widget import PlanningControlPanelWidget
from ui.widgets.planning_legend_widget import PlanningLegendWidget


class PlanningView(ft.Container):
    """
    Orchestrates the Urban Planning layout composite view.
    Follows Clean Architecture Composite Container and delegates business logic to PlanningController.
    """

    def __init__(
        self,
        locale_manager: LocaleManager,
        control_client: Optional[Any] = None,
        sas_result_queue: Optional[Any] = None,
        client: Optional[Any] = None,
        controller: Optional[PlanningController] = None,
    ):
        super().__init__(expand=True)
        self.locale_manager = locale_manager
        self.control_client = control_client

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

        # Visual subcomponents
        self.planning_control_panel = PlanningControlPanelWidget(
            locale_manager=self.locale_manager,
            on_close_details=self._handle_panel_close,
            on_filter_change=self._handle_filter_change,
        )

        self.map_widget = InteractiveMap(
            project_root=project_root,
            on_node_click=self._handle_node_click,
            on_edge_click=self._handle_edge_click,
            on_topology_loaded=self._on_topology_loaded,
        )

        self.legend_widget = PlanningLegendWidget(locale_manager=self.locale_manager)

        self.command_bar_widget = PlanningCommandBarWidget(
            on_analyze_click=self._load_analysis_click,
            on_save_report_click=self._save_report_click,
            locale_manager=self.locale_manager,
        )

        self.map_container = ft.Column(
            controls=[self.map_widget, self.legend_widget],
            expand=True,
            spacing=5,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

        self.main_content = ft.Row(
            controls=[
                ft.Container(content=self.map_container, expand=True, alignment=ft.alignment.center),
                self.planning_control_panel,
            ],
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

        self.content = ft.Column(
            controls=[self.main_content, self.command_bar_widget],
            expand=True,
            spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

    # Backward compatibility properties
    @property
    def client(self) -> Any:
        return self.controller.client

    @client.setter
    def client(self, value: Any) -> None:
        self.controller.client = value

    @property
    def last_report_content(self) -> Optional[str]:
        return self.controller.last_report_content

    @last_report_content.setter
    def last_report_content(self, value: Optional[str]) -> None:
        self.controller.last_report_content = value

    @property
    def last_scenario_dir(self) -> Optional[str]:
        return self.controller.last_scenario_dir

    @last_scenario_dir.setter
    def last_scenario_dir(self, value: Optional[str]) -> None:
        self.controller.last_scenario_dir = value

    @property
    def is_analyzing(self) -> bool:
        return self.controller.is_analyzing

    @is_analyzing.setter
    def is_analyzing(self, value: bool) -> None:
        self.controller.is_analyzing = value

    @property
    def analyze_button(self) -> Any:
        return self.command_bar_widget.analyze_button

    @property
    def save_report_button(self) -> Any:
        return self.command_bar_widget.save_report_button

    @property
    def status_text(self) -> Any:
        return self.command_bar_widget.status_text

    @property
    def command_bar(self) -> Any:
        return self.command_bar_widget

    @property
    def legend_bar(self) -> Any:
        return self.legend_widget

    # Event handlers
    def _handle_node_click(self, node_id: str) -> None:
        if self.map_widget:
            self.map_widget.set_selected_node(node_id)
        if self.planning_control_panel:
            self.planning_control_panel.show_node_details(node_id)
        if self.page:
            self.page.snack_bar = ft.SnackBar(content=ft.Text(f"Semáforo/Nó selecionado: {node_id}"))
            self.page.snack_bar.open = True
            self.page.update()

    def _handle_edge_click(self, edge_id: str, edge_data: dict) -> None:
        if self.map_widget:
            self.map_widget.set_selected_edge(edge_id)
        if self.planning_control_panel:
            self.planning_control_panel.show_edge_details(edge_id, edge_data)
        if self.page:
            edge_name = edge_data.get("name", edge_id) if isinstance(edge_data, dict) else edge_id
            self.page.snack_bar = ft.SnackBar(content=ft.Text(f"Via/Rua selecionada: {edge_name}"))
            self.page.snack_bar.open = True
            self.page.update()

    def _handle_panel_close(self) -> None:
        if self.map_widget:
            self.map_widget.set_selected_node(None)
            self.map_widget.set_selected_edge(None)

    def _handle_filter_change(self, filter_key: str) -> None:
        if self.map_widget:
            self.map_widget.set_filter(filter_key)

    def did_mount(self) -> None:
        self.page.overlay.append(self.file_picker)
        self.update_translations(self.locale_manager)
        self.load_map()
        self.page.update()

    def load_map(self) -> None:
        if self.map_widget:
            self.map_widget.load_map()

    def _on_topology_loaded(self) -> None:
        if self.map_widget and self.planning_control_panel and self.map_widget.topology:
            self.planning_control_panel.set_topology(self.map_widget.topology)

        if self.is_analyzing:
            return
        self.analyze_button.disabled = False
        status = (
            self.locale_manager.get_string(
                "planning_view.status_ready", default="Topologia carregada. Pronto para análise."
            )
            if self.locale_manager
            else "Topologia carregada. Pronto para análise."
        )
        self.command_bar_widget.set_status(status, italic=True, color=None)
        self.update()

    def update_translations(self, lm: LocaleManager) -> None:
        self.legend_widget.update_translations(lm)
        self.command_bar_widget.update_translations(lm, is_analyzing=self.is_analyzing)

    def _load_analysis_click(self, e: Any) -> None:
        if self.map_widget:
            self.map_widget.set_recommendations({})
        if self.planning_control_panel:
            self.planning_control_panel.hide_node_details()
            self.planning_control_panel.update_analysis_results({})

        self.analyze_button.disabled = True
        self.save_report_button.disabled = True

        status = (
            self.locale_manager.get_string(
                "planning_view.status_processing",
                default="Processando análise e gerando laudo por inteligência artificial... Por favor, aguarde.",
            )
            if self.locale_manager
            else "Processando análise e gerando laudo por inteligência artificial... Por favor, aguarde."
        )

        self.command_bar_widget.set_status(status, italic=False, color=ft.Colors.CYAN)
        self.update()

        self.map_widget.load_map()
        self.controller.trigger_analysis()

    def _on_analysis_complete(self, response: dict) -> None:
        try:
            self._process_analysis_response(response)
        except Exception as ex:
            logging.error(f"[PLANNING_VIEW] Error processing analysis response: {ex}", exc_info=True)

    def _process_analysis_response(self, response: dict) -> None:
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

    def _save_report_click(self, e: Any) -> None:
        if not self.last_report_content:
            return
        PlanningExportHandler.request_save_file(self.file_picker, self.locale_manager)

    def _on_save_result(self, e: ft.FilePickerResultEvent) -> None:
        PlanningExportHandler.on_save_result(
            e=e,
            last_report_content=self.last_report_content,
            controller=self.controller,
            page=self.page,
            command_bar_widget=self.command_bar_widget,
            locale_manager=self.locale_manager,
            update_callback=self.update,
        )
