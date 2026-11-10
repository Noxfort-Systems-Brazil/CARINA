# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Defines the AdvancedDQNCard, a component widget for the Settings screen.
"""

from typing import Any, Dict

import flet as ft

# --- CHANGE 1: Import LocaleManager for type annotation ---
from ui.handlers.locale_manager import LocaleManager


class AdvancedDQNCard(ft.Card):
    """
    A Card encapsulating advanced DQN Agent settings.
    """

    def __init__(self, initial_values: Dict[str, Any]):
        """
        Initializes the Card with the provided values.
        """
        super().__init__()

        numeric_filter = ft.InputFilter(allow=True, regex_string=r"[0-9.-]")

        # --- Controls ---
        self.title_text = ft.Text(size=18, weight=ft.FontWeight.BOLD)
        self.tf_dqn_epsilon_decay = ft.TextField(
            value=initial_values.get("dqn_epsilon_decay", "30000"), input_filter=numeric_filter
        )
        self.tf_dqn_batch_size = ft.TextField(
            value=initial_values.get("dqn_batch_size", "128"), input_filter=numeric_filter
        )

        # --- Card Structure ---
        self.content = ft.Container(
            padding=15,
            content=ft.Column([self.title_text, ft.Divider(), self.tf_dqn_epsilon_decay, self.tf_dqn_batch_size]),
        )

    def get_values(self) -> Dict[str, Any]:
        """
        Returns a dictionary with current control values in this card.
        """
        return {
            "dqn_epsilon_decay": self.tf_dqn_epsilon_decay.value,
            "dqn_batch_size": self.tf_dqn_batch_size.value,
        }

    def set_values(self, values: Dict[str, Any]):
        """
        Updates control values in this card based on the provided dictionary.
        """
        self.tf_dqn_epsilon_decay.value = values.get("dqn_epsilon_decay", "30000")
        self.tf_dqn_batch_size.value = values.get("dqn_batch_size", "128")
        if self.page:
            self.update()

    # --- CHANGE 2: New method to translate the widget ---
    def update_translations(self, lm: LocaleManager):
        """Updates texts in this card based on the LocaleManager."""
        self.title_text.value = lm.get_string("settings_view.advanced_dqn_card.title")
        self.tf_dqn_epsilon_decay.label = lm.get_string("settings_view.advanced_dqn_card.epsilon_decay")
        self.tf_dqn_batch_size.label = lm.get_string("settings_view.advanced_dqn_card.batch_size")
        if self.page:
            self.update()
