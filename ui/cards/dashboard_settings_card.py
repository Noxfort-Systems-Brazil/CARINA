# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Defines the DashboardSettingsCard, a component widget for the Settings screen.
"""

from typing import Any, Dict

import flet as ft

# --- CHANGE 1: Import LocaleManager for type annotation ---
from ui.handlers.locale_manager import LocaleManager


class DashboardSettingsCard(ft.Card):
    """
    A Card encapsulating visualization and dashboard settings.
    """

    def __init__(self, initial_values: Dict[str, Any]):
        """
        Initializes the Card with the provided values.
        """
        super().__init__()

        numeric_filter = ft.InputFilter(allow=True, regex_string=r"[0-9.-]")

        # --- Controls ---
        self.title_text = ft.Text(size=18, weight=ft.FontWeight.BOLD)
        self.dd_heatmap_strategy = ft.Dropdown(
            options=[ft.dropdown.Option("max"), ft.dropdown.Option("average")],
            value=initial_values.get("heatmap_strategy", "max"),
            width=270,
        )
        self.tf_heatmap_saturation = ft.TextField(
            value=initial_values.get("heatmap_saturation", "100.0"), input_filter=numeric_filter
        )

        # --- Card Structure ---
        self.content = ft.Container(
            padding=15,
            content=ft.Column(
                [
                    self.title_text,
                    ft.Divider(),
                    ft.Container(height=5),
                    self.dd_heatmap_strategy,
                    self.tf_heatmap_saturation,
                ]
            ),
        )

    def get_values(self) -> Dict[str, Any]:
        """
        Returns a dictionary with current control values in this card.
        """
        return {
            "heatmap_strategy": self.dd_heatmap_strategy.value,
            "heatmap_saturation": self.tf_heatmap_saturation.value,
        }

    def set_values(self, values: Dict[str, Any]):
        """
        Updates control values in this card based on the provided dictionary.
        """
        self.dd_heatmap_strategy.value = values.get("heatmap_strategy", "max")
        self.tf_heatmap_saturation.value = values.get("heatmap_saturation", "100.0")
        if self.page:
            self.update()

    # --- CHANGE 2: New method to translate the widget ---
    def update_translations(self, lm: LocaleManager):
        """Updates texts in this card based on the LocaleManager."""
        # Assuming corresponding keys exist in JSON files
        self.title_text.value = lm.get_string("settings_view.dashboard_card.title")
        self.dd_heatmap_strategy.label = lm.get_string("settings_view.dashboard_card.heatmap_strategy")
        self.tf_heatmap_saturation.label = lm.get_string("settings_view.dashboard_card.heatmap_saturation")
        if self.page:
            self.update()
