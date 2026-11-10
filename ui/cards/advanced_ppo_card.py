# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Defines the AdvancedPPOCard, a component widget for the Settings screen.
"""

from typing import Any, Dict

import flet as ft

# --- CHANGE 1: Import LocaleManager for type annotation ---
from ui.handlers.locale_manager import LocaleManager


class AdvancedPPOCard(ft.Card):
    """
    A Card encapsulating advanced PPO Agent settings.
    """

    def __init__(self, initial_values: Dict[str, Any]):
        """
        Initializes the Card with the provided values.
        """
        super().__init__()

        numeric_filter = ft.InputFilter(allow=True, regex_string=r"[0-9.-]")

        # --- Controls ---
        self.title_text = ft.Text(size=18, weight=ft.FontWeight.BOLD)
        self.tf_ppo_gamma = ft.TextField(value=initial_values.get("ppo_gamma", "0.99"), input_filter=numeric_filter)
        self.tf_ppo_k_epochs = ft.TextField(value=initial_values.get("ppo_k_epochs", "4"), input_filter=numeric_filter)
        self.tf_ppo_eps_clip = ft.TextField(
            value=initial_values.get("ppo_eps_clip", "0.2"), input_filter=numeric_filter
        )

        # --- Card Structure ---
        self.content = ft.Container(
            padding=15,
            content=ft.Column(
                [
                    self.title_text,
                    ft.Divider(),
                    self.tf_ppo_gamma,
                    self.tf_ppo_k_epochs,
                    self.tf_ppo_eps_clip,
                ]
            ),
        )

    def get_values(self) -> Dict[str, Any]:
        """
        Returns a dictionary with current control values in this card.
        """
        return {
            "ppo_gamma": self.tf_ppo_gamma.value,
            "ppo_k_epochs": self.tf_ppo_k_epochs.value,
            "ppo_eps_clip": self.tf_ppo_eps_clip.value,
        }

    def set_values(self, values: Dict[str, Any]):
        """
        Updates control values in this card based on the provided dictionary.
        """
        self.tf_ppo_gamma.value = values.get("ppo_gamma", "0.99")
        self.tf_ppo_k_epochs.value = values.get("ppo_k_epochs", "4")
        self.tf_ppo_eps_clip.value = values.get("ppo_eps_clip", "0.2")
        if self.page:
            self.update()

    # --- CHANGE 2: New method to translate the widget ---
    def update_translations(self, lm: LocaleManager):
        """Updates texts in this card based on the LocaleManager."""
        self.title_text.value = lm.get_string("settings_view.advanced_ppo_card.title")
        self.tf_ppo_gamma.label = lm.get_string("settings_view.advanced_ppo_card.gamma")
        self.tf_ppo_k_epochs.label = lm.get_string("settings_view.advanced_ppo_card.k_epochs")
        self.tf_ppo_eps_clip.label = lm.get_string("settings_view.advanced_ppo_card.eps_clip")
        if self.page:
            self.update()
