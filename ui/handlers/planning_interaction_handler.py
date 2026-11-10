# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Any, Optional, Tuple

import flet as ft
from ui.handlers.locale_manager import LocaleManager
from ui.managers.alias_manager import AliasManager


class PlanningInteractionHandler:
    """Handles node/edge selection events, snackbar notifications, and analysis status formatting."""

    @staticmethod
    def show_snack_bar(page: Optional[ft.Page], text: str) -> None:
        """Displays transient status bar message on the active page."""
        if page:
            page.snack_bar = ft.SnackBar(content=ft.Text(text))
            page.snack_bar.open = True
            page.update()

    @classmethod
    def handle_node_selection(
        cls,
        node_id: Optional[str],
        map_widget: Any,
        control_panel: Any,
        locale_manager: Optional[LocaleManager],
        page: Optional[ft.Page],
    ) -> None:
        """Synchronizes node selection across the map canvas and control panel."""
        if map_widget:
            map_widget.set_selected_node(node_id)
        if control_panel:
            if node_id:
                control_panel.show_node_details(node_id)
            else:
                control_panel.hide_node_details()
        if node_id:
            msg = (
                locale_manager.get_string("planning_view.node_selected", default="Semáforo/Nó selecionado: {id}", id=node_id)
                if locale_manager
                else f"Semáforo/Nó selecionado: {node_id}"
            )
            cls.show_snack_bar(page, msg)

    @classmethod
    def handle_edge_selection(
        cls,
        edge_id: Optional[str],
        edge_data: dict,
        map_widget: Any,
        control_panel: Any,
        locale_manager: Optional[LocaleManager],
        page: Optional[ft.Page],
    ) -> None:
        """Synchronizes street/edge selection and extracts human-readable aliases."""
        if map_widget:
            map_widget.set_selected_edge(edge_id)
        if control_panel:
            if edge_id:
                control_panel.show_edge_details(edge_id, edge_data)
            else:
                control_panel.hide_node_details()
        if edge_id:
            alias_mgr = AliasManager()
            default_name = edge_data.get("name") if isinstance(edge_data, dict) else None
            edge_name = alias_mgr.get_alias(edge_id, default=default_name)
            msg = (
                locale_manager.get_string("planning_view.street_selected", default="Via/Rua selecionada: {name}", name=edge_name)
                if locale_manager
                else f"Via/Rua selecionada: {edge_name}"
            )
            cls.show_snack_bar(page, msg)

    @staticmethod
    def format_analysis_ui_state(
        processed: dict,
        locale_manager: Optional[LocaleManager],
    ) -> Tuple[str, Any, bool]:
        """
        Determines the status message, theme color, and save button state from processed analysis.
        Returns: (status_text, status_color, has_recommendations)
        """
        if processed.get("status") == "error":
            return processed.get("message", "Error"), ft.Colors.RED, False

        if processed.get("significant_change") is False:
            status = (
                locale_manager.get_string("planning_view.status_loaded_no_change")
                if locale_manager
                else "Análise concluída (sem alterações significativas)."
            )
            color = ft.Colors.AMBER
        else:
            status = (
                locale_manager.get_string("planning_view.status_loaded_with_change")
                if locale_manager
                else "Análise concluída com sucesso."
            )
            color = ft.Colors.GREEN

        return status, color, True
