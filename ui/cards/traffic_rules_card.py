# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Defines the TrafficRulesCard, a component widget for the Settings screen.
"""

from typing import Any, Dict

import flet as ft

# --- CHANGE 1: Import LocaleManager for type annotation ---
from ui.handlers.locale_manager import LocaleManager


class TrafficRulesCard(ft.Card):
    """
    A Card encapsulating traffic rule settings.
    """

    def __init__(self, initial_values: Dict[str, Any]):
        """
        Initializes the Card with the provided values.
        """
        super().__init__()

        numeric_filter = ft.InputFilter(allow=True, regex_string=r"[0-9.-]")

        # --- Controls ---
        self.title_text = ft.Text(size=18, weight=ft.FontWeight.BOLD)
        self.tf_min_green_time = ft.TextField(
            value=initial_values.get("min_green_time", "10"), input_filter=numeric_filter
        )
        self.tf_yellow_time = ft.TextField(value=initial_values.get("yellow_time", "3"), input_filter=numeric_filter)

        # --- Card Structure ---
        self.content = ft.Container(
            padding=15, content=ft.Column([self.title_text, ft.Divider(), self.tf_min_green_time, self.tf_yellow_time])
        )

    def get_values(self) -> Dict[str, Any]:
        """
        Returns a dictionary with current control values in this card.
        """
        return {
            "min_green_time": self.tf_min_green_time.value,
            "yellow_time": self.tf_yellow_time.value,
        }

    def set_values(self, values: Dict[str, Any]):
        """
        Updates control values in this card based on the provided dictionary.
        """
        self.tf_min_green_time.value = str(values.get("min_green_time", "10"))
        self.tf_yellow_time.value = str(values.get("yellow_time", values.get("yellow_time_seconds", "3")))
        if self.page:
            self.update()

    # --- CHANGE 2: New method to translate the widget ---
    def update_translations(self, lm: LocaleManager):
        """Updates texts in this card based on the LocaleManager."""
        # Assuming corresponding keys exist in JSON files
        self.title_text.value = lm.get_string("settings_view.traffic_rules_card.title")
        self.tf_min_green_time.label = lm.get_string("settings_view.traffic_rules_card.min_green_time")
        self.tf_yellow_time.label = lm.get_string("settings_view.traffic_rules_card.yellow_time")
        if self.page:
            self.update()
