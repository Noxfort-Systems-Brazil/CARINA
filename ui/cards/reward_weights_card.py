# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Defines the RewardWeightsCard, a component widget for the Settings screen.
"""

import os
from typing import Any, Dict

import flet as ft

# --- CHANGE 1: Import LocaleManager for type annotation ---
from ui.handlers.locale_manager import LocaleManager


class RewardWeightsCard(ft.Card):
    """
    A Card encapsulating reward weight settings.
    """

    def __init__(self, initial_values: Dict[str, Any]):
        """
        Initializes the Card with the provided values.
        """
        super().__init__()

        numeric_filter = ft.InputFilter(allow=True, regex_string=r"[0-9.-]")

        # --- Controls ---
        self.title_text = ft.Text(size=18, weight=ft.FontWeight.BOLD)
        self.description_text = ft.Text(italic=True, size=12, color=ft.Colors.WHITE70)

        auto_enabled = str(initial_values.get("auto_reward_weights_enabled", "True")).lower() in (
            "true",
            "1",
            "yes",
        )
        self.sw_auto_reward_weights = ft.Switch(
            value=auto_enabled,
            on_change=self._on_auto_reward_weights_toggle,
        )

        self.tf_weight_waiting_time = ft.TextField(
            value=str(initial_values.get("weight_waiting_time", "-2.0")),
            input_filter=numeric_filter,
            disabled=auto_enabled,
        )
        self.tf_weight_flow = ft.TextField(
            value=str(initial_values.get("weight_flow", "2.0")),
            input_filter=numeric_filter,
            disabled=auto_enabled,
        )

        if auto_enabled and str(initial_values.get("weight_waiting_time", "-2.0")) == "-2.0" and str(initial_values.get("weight_flow", "2.0")) == "2.0":
            self._recalculate_weights()

        # --- Card Structure ---
        self.content = ft.Container(
            padding=15,
            content=ft.Column(
                [
                    self.title_text,
                    ft.Divider(),
                    self.description_text,
                    self.sw_auto_reward_weights,
                    self.tf_weight_waiting_time,
                    self.tf_weight_flow,
                ]
            ),
        )

    def _recalculate_weights(self):
        try:
            from engine.reward_weights_calculator import RewardWeightsCalculator
            net = None
            try:
                from controller.map_discoverer import MapTopologyDiscoverer
                import sumolib
                map_file = MapTopologyDiscoverer.get_map_file()
                if map_file and os.path.exists(map_file):
                    net = sumolib.net.readNet(map_file, withInternal=False)
            except Exception:
                pass
            w_wait, w_flow = RewardWeightsCalculator.calculate_from_topology(net)
            self.tf_weight_waiting_time.value = str(w_wait)
            self.tf_weight_flow.value = str(w_flow)
        except Exception:
            pass

    def _on_auto_reward_weights_toggle(self, e):
        """Disables or enables manual reward weight inputs depending on auto switch."""
        is_auto = self.sw_auto_reward_weights.value
        self.tf_weight_waiting_time.disabled = is_auto
        self.tf_weight_flow.disabled = is_auto
        if is_auto:
            self._recalculate_weights()
        if self.page:
            self.update()

    def get_values(self) -> Dict[str, Any]:
        """
        Returns a dictionary with current control values in this card.
        """
        return {
            "auto_reward_weights_enabled": self.sw_auto_reward_weights.value,
            "weight_waiting_time": self.tf_weight_waiting_time.value,
            "weight_flow": self.tf_weight_flow.value,
        }

    def set_values(self, values: Dict[str, Any]):
        """
        Updates control values in this card based on the provided dictionary.
        """
        auto_enabled = str(values.get("auto_reward_weights_enabled", "True")).lower() in (
            "true",
            "1",
            "yes",
        )
        self.sw_auto_reward_weights.value = auto_enabled
        self.tf_weight_waiting_time.disabled = auto_enabled
        self.tf_weight_flow.disabled = auto_enabled
        w_wait = str(values.get("weight_waiting_time", "-2.0"))
        w_flow = str(values.get("weight_flow", "2.0"))
        self.tf_weight_waiting_time.value = w_wait
        self.tf_weight_flow.value = w_flow
        if auto_enabled and w_wait == "-2.0" and w_flow == "2.0":
            self._recalculate_weights()

        if self.page:
            self.update()

    # --- CHANGE 2: New method to translate the widget ---
    def update_translations(self, lm: LocaleManager):
        """Updates texts in this card based on the LocaleManager."""
        self.title_text.value = lm.get_string("settings_view.reward_weights_card.title")
        self.description_text.value = lm.get_string("settings_view.reward_weights_card.description")

        self.sw_auto_reward_weights.label = lm.get_string(
            "settings_view.reward_weights_card.auto_reward_weights",
            default="Cálculo Automático de Pesos (Equilíbrio da Malha)",
        )
        self.tf_weight_waiting_time.label = lm.get_string("settings_view.reward_weights_card.waiting_time_label")
        self.tf_weight_waiting_time.tooltip = lm.get_string("settings_view.reward_weights_card.waiting_time_tooltip")

        self.tf_weight_flow.label = lm.get_string("settings_view.reward_weights_card.flow_label")
        self.tf_weight_flow.tooltip = lm.get_string("settings_view.reward_weights_card.flow_tooltip")

        if self.page:
            self.update()
