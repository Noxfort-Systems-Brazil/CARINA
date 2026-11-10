# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Defines the PilotingSchoolCard, a component widget for the Settings screen.
Delegates physical calculations to PilotingSchoolCalculator and UI pacing display
to PilotingSchoolPacingBanner (SRP / Clean Architecture).
"""

from typing import Any, Dict, Optional

import flet as ft

from ui.components.piloting_school_pacing_banner import PilotingSchoolPacingBanner
from ui.controllers.piloting_school_calculator import PilotingSchoolCalculator
from ui.handlers.locale_manager import LocaleManager


class PilotingSchoolCard(ft.Card):
    """A Card encapsulating Piloting School settings and curriculum pacing."""

    def __init__(self, initial_values: Dict[str, Any]):
        super().__init__()

        numeric_filter = ft.InputFilter(allow=True, regex_string=r"[0-9.-]")
        self._last_lm: Optional[LocaleManager] = None

        # Banner subcomponent
        self._banner = PilotingSchoolPacingBanner()
        self.pacing_info_container = self._banner.container
        self.lbl_pacing_info_title = self._banner.lbl_pacing_info_title
        self.lbl_steps_per_episode = self._banner.lbl_steps_per_episode
        self.lbl_inviolable_floor = self._banner.lbl_inviolable_floor
        self.lbl_topology_summary = self._banner.lbl_topology_summary

        # Calculated Pacing Metadata
        self.calculated_steps = 1800
        self.calculated_duration = 450.0
        self.calculated_min_episodes = 1344
        self.calculated_complexity = 1.0
        self.calculated_signals = 0
        self.calculated_connections = 0

        # Controls
        self.title_text = ft.Text(size=18, weight=ft.FontWeight.BOLD)
        auto_enabled = str(initial_values.get("auto_pacing_enabled", "True")).lower() in ("true", "1", "yes")
        self.sw_auto_pacing = ft.Switch(value=auto_enabled, on_change=self._on_auto_pacing_toggle)

        self.tf_child_phase_episodes = ft.TextField(
            value=str(initial_values.get("child_phase_episodes", "1")),
            input_filter=numeric_filter,
            disabled=auto_enabled,
            on_change=self._on_episode_input_change,
        )
        self.tf_teen_phase_min_episodes = ft.TextField(
            value=str(initial_values.get("teen_phase_min_episodes", "1")),
            input_filter=numeric_filter,
            disabled=auto_enabled,
            on_change=self._on_episode_input_change,
        )

        auto_margin_enabled = str(initial_values.get("auto_performance_margin_enabled", "True")).lower() in (
            "true",
            "1",
            "yes",
        )
        self.sw_auto_performance_margin = ft.Switch(
            value=auto_margin_enabled,
            on_change=self._on_auto_margin_toggle,
        )
        self.tf_performance_margin = ft.TextField(
            value=str(initial_values.get("performance_margin", "-100.0")),
            input_filter=numeric_filter,
            disabled=auto_margin_enabled,
        )

        self._recalculate_pacing()
        if auto_margin_enabled and str(initial_values.get("performance_margin", "-100.0")) == "-100.0":
            self._recalculate_margin()

        # Layout
        self.content = ft.Container(
            padding=15,
            content=ft.Column(
                [
                    self.title_text,
                    ft.Divider(),
                    self.pacing_info_container,
                    self.sw_auto_pacing,
                    self.tf_child_phase_episodes,
                    self.tf_teen_phase_min_episodes,
                    ft.Divider(height=1, thickness=0.5),
                    self.sw_auto_performance_margin,
                    self.tf_performance_margin,
                ]
            ),
        )

    def _update_pacing_labels(self):
        """Updates text descriptions in the pacing banner and helper texts."""
        self._banner.update_labels(
            steps=self.calculated_steps,
            duration=self.calculated_duration,
            min_episodes=self.calculated_min_episodes,
            signals=self.calculated_signals,
            connections=self.calculated_connections,
            complexity=self.calculated_complexity,
            lm=self._last_lm,
        )
        min_ep = self.calculated_min_episodes
        helper = (
            self._last_lm.get_string(
                "settings_view.piloting_school_card.min_episodes_helper",
                default=f"Piso mínimo inviolável: {min_ep} episódios (1 semana)",
                min_episodes=min_ep,
            )
            if self._last_lm
            else f"Piso mínimo inviolável: {min_ep} episódios (1 semana)"
        )
        self.tf_child_phase_episodes.helper_text = helper
        self.tf_teen_phase_min_episodes.helper_text = helper

    def _validate_minimums(self):
        """Checks manual values against the weekly safety floor and displays error/warning if below."""
        if self.sw_auto_pacing.value:
            self.tf_child_phase_episodes.error_text = None
            self.tf_teen_phase_min_episodes.error_text = None
            return

        min_ep = self.calculated_min_episodes
        warning_msg = (
            self._last_lm.get_string(
                "settings_view.piloting_school_card.below_floor_warning",
                default=f"Aviso: valor abaixo do piso inviolável de 1 semana ({min_ep} episódios)",
                min_episodes=min_ep,
            )
            if self._last_lm
            else f"Aviso: valor abaixo do piso inviolável de 1 semana ({min_ep} episódios)"
        )

        try:
            c_val = int(float(self.tf_child_phase_episodes.value or 0))
            self.tf_child_phase_episodes.error_text = warning_msg if c_val < min_ep else None
        except (ValueError, TypeError):
            self.tf_child_phase_episodes.error_text = None

        try:
            t_val = int(float(self.tf_teen_phase_min_episodes.value or 0))
            self.tf_teen_phase_min_episodes.error_text = warning_msg if t_val < min_ep else None
        except (ValueError, TypeError):
            self.tf_teen_phase_min_episodes.error_text = None

    def _on_episode_input_change(self, e):
        """Validates inputs whenever the user modifies them."""
        self._validate_minimums()
        if self.page:
            self.update()

    def _recalculate_pacing(self):
        """Calculates physical pacing and updates control values."""
        res = PilotingSchoolCalculator.calculate_pacing()
        self.calculated_steps = res.steps
        self.calculated_duration = res.duration
        self.calculated_min_episodes = res.min_episodes
        self.calculated_complexity = res.complexity
        self.calculated_signals = res.signals
        self.calculated_connections = res.connections

        if self.sw_auto_pacing.value:
            self.tf_child_phase_episodes.value = str(res.child_episodes)
            self.tf_teen_phase_min_episodes.value = str(res.teen_episodes)

        self._validate_minimums()
        self._update_pacing_labels()

    def _recalculate_margin(self):
        """Calculates performance margin from topology."""
        margin = PilotingSchoolCalculator.calculate_margin()
        self.tf_performance_margin.value = str(margin)

    def _on_auto_pacing_toggle(self, e):
        """Disables or enables manual phase inputs depending on auto-pacing switch."""
        is_auto = self.sw_auto_pacing.value
        self.tf_child_phase_episodes.disabled = is_auto
        self.tf_teen_phase_min_episodes.disabled = is_auto
        if is_auto:
            self._recalculate_pacing()
        else:
            self._validate_minimums()
        if self.page:
            self.update()

    def _on_auto_margin_toggle(self, e):
        """Disables or enables manual margin input depending on auto-margin switch."""
        is_auto = self.sw_auto_performance_margin.value
        self.tf_performance_margin.disabled = is_auto
        if is_auto:
            self._recalculate_margin()
        if self.page:
            self.update()

    def get_values(self) -> Dict[str, Any]:
        """Returns current control values, clamping below-floor inputs to the safety floor."""
        try:
            val_c = int(float(self.tf_child_phase_episodes.value or 0))
            if not self.sw_auto_pacing.value and val_c < self.calculated_min_episodes:
                val_c = self.calculated_min_episodes
                self.tf_child_phase_episodes.value = str(val_c)
        except (ValueError, TypeError):
            val_c = self.calculated_min_episodes

        try:
            val_t = int(float(self.tf_teen_phase_min_episodes.value or 0))
            if not self.sw_auto_pacing.value and val_t < self.calculated_min_episodes:
                val_t = self.calculated_min_episodes
                self.tf_teen_phase_min_episodes.value = str(val_t)
        except (ValueError, TypeError):
            val_t = self.calculated_min_episodes

        return {
            "auto_pacing_enabled": self.sw_auto_pacing.value,
            "child_phase_episodes": str(val_c),
            "teen_phase_min_episodes": str(val_t),
            "auto_performance_margin_enabled": self.sw_auto_performance_margin.value,
            "performance_margin": self.tf_performance_margin.value,
        }

    def set_values(self, values: Dict[str, Any]):
        """Updates control values in this card based on the provided dictionary."""
        auto_enabled = str(values.get("auto_pacing_enabled", "True")).lower() in ("true", "1", "yes")
        self.sw_auto_pacing.value = auto_enabled
        self.tf_child_phase_episodes.disabled = auto_enabled
        self.tf_teen_phase_min_episodes.disabled = auto_enabled
        c_ep = str(values.get("child_phase_episodes", "1"))
        t_ep = str(values.get("teen_phase_min_episodes", "1"))
        self.tf_child_phase_episodes.value = c_ep
        self.tf_teen_phase_min_episodes.value = t_ep
        if auto_enabled and c_ep == "1" and t_ep == "1":
            self._recalculate_pacing()
        else:
            self._validate_minimums()

        auto_margin_enabled = str(values.get("auto_performance_margin_enabled", "True")).lower() in (
            "true",
            "1",
            "yes",
        )
        self.sw_auto_performance_margin.value = auto_margin_enabled
        self.tf_performance_margin.disabled = auto_margin_enabled
        p_margin = str(values.get("performance_margin", "-100.0"))
        self.tf_performance_margin.value = p_margin
        if auto_margin_enabled and p_margin == "-100.0":
            self._recalculate_margin()

        self._update_pacing_labels()
        if self.page:
            self.update()

    def update_translations(self, lm: LocaleManager):
        """Updates texts in this card based on the LocaleManager."""
        self._last_lm = lm
        self.title_text.value = lm.get_string("settings_view.piloting_school_card.title")
        self.sw_auto_pacing.label = lm.get_string(
            "settings_view.piloting_school_card.auto_pacing",
            default="Cálculo Automático de Duração (ao carregar mapa)",
        )
        self.tf_child_phase_episodes.label = lm.get_string("settings_view.piloting_school_card.child_phase_duration")
        self.tf_teen_phase_min_episodes.label = lm.get_string("settings_view.piloting_school_card.teen_phase_duration")
        self.sw_auto_performance_margin.label = lm.get_string(
            "settings_view.piloting_school_card.auto_performance_margin",
            default="Cálculo Automático de Margem (Fluidodinâmica)",
        )
        self.tf_performance_margin.label = lm.get_string(
            "settings_view.piloting_school_card.performance_margin",
            default=lm.get_string(
                "settings_view.advanced_ppo_card.performance_margin",
                default="Margem de Performance para Graduação (%)",
            ),
        )
        self._update_pacing_labels()
        self._validate_minimums()
        if self.page:
            self.update()
