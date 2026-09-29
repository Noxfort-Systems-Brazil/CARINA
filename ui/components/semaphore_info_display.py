# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: ui/components/semaphore_info_display.py
# Author: Gabriel Moraes
# Date: September 2026

import logging
from typing import Any, Dict, Optional

import flet as ft

from ui.components.hardware_status_panel import HardwareStatusPanel
from ui.components.lane_states_panel import LaneStatesPanel
from ui.handlers.locale_manager import LocaleManager
from ui.managers.alias_manager import AliasManager


class SemaphoreInfoDisplayWidget(ft.Column):
    """
    Widget displaying static semaphore details, hardware metadata, maturity phase, and lane states.
    Follows Clean Architecture Composite Widget pattern.
    """

    def __init__(self, locale_manager: LocaleManager):
        super().__init__()
        self.locale_manager = locale_manager
        self.alias_manager = AliasManager()
        self._current_semaphore_id: Optional[str] = None
        self.semaphore_id_text_template = ""

        self.semaphore_id_text = ft.TextField(
            text_size=14,
            height=40,
            expand=True,
            on_submit=self._on_submit,
            on_blur=self._on_submit,
            tooltip=self.locale_manager.get_string(
                "semaphore_info.save_tooltip", default="Pressione Enter para salvar"
            ),
        )
        self.maturity_phase_label = ft.Text(size=12, color=ft.Colors.WHITE54)
        self.maturity_phase_text = ft.Text("---", weight=ft.FontWeight.BOLD, size=16)

        # Specialized Subcomponents (SRP)
        self.hardware_panel = HardwareStatusPanel(locale_manager)
        self.lane_states_panel = LaneStatesPanel(locale_manager, self.alias_manager)

        self.controls = [
            ft.Row(
                [ft.Icon(ft.Icons.TRAFFIC_ROUNDED), self.semaphore_id_text],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            self.hardware_panel,
            ft.Row(
                [
                    ft.Icon(ft.Icons.SCHOOL_ROUNDED, color=ft.Colors.WHITE54, size=30),
                    ft.Column(
                        [self.maturity_phase_label, self.maturity_phase_text],
                        spacing=2,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=15,
            ),
            ft.Divider(height=10),
            self.lane_states_panel,
        ]
        self.horizontal_alignment = ft.CrossAxisAlignment.STRETCH
        self.spacing = 8

    def did_mount(self) -> None:
        self.update_translations(self.locale_manager)
        if self.page:
            self.update()

    def update_translations(self, lm: LocaleManager) -> None:
        self.locale_manager = lm
        self.semaphore_id_text_template = lm.get_string("dashboard_view.semaphore_controls_title_prefix")
        self.semaphore_id_text.label = self.semaphore_id_text_template
        self.semaphore_id_text.tooltip = lm.get_string(
            "semaphore_info.save_tooltip", default="Pressione Enter para salvar"
        )
        self.maturity_phase_label.value = lm.get_string("dashboard_view.maturity_phase_label")

        self.hardware_panel.update_translations(lm)
        self.lane_states_panel.update_translations(lm)

        if self.page:
            self.update()

    def update_info(self, semaphore_id: str, phase_key: str, semaphore_data: Dict) -> None:
        """Updates UI components with the latest telemetry and signal states."""
        if self._current_semaphore_id != semaphore_id:
            self._current_semaphore_id = semaphore_id
            self.semaphore_id_text.value = self.alias_manager.get_alias(semaphore_id)

        # 1. Update hardware status
        self.hardware_panel.update_hardware_info(semaphore_id, semaphore_data)

        # 2. Update maturity phase
        translation_key = f"maturity_phases.{phase_key.upper()}"
        translated_phase = self.locale_manager.get_string(translation_key)
        if translated_phase == translation_key:
            translated_phase = self.locale_manager.get_string("maturity_phases.UNKNOWN")
        self.maturity_phase_text.value = translated_phase

        phase_colors = {
            "ADULT": ft.Colors.GREEN_ACCENT_400,
            "TEEN": ft.Colors.AMBER_ACCENT_400,
            "CHILD": ft.Colors.CYAN_ACCENT_400,
        }
        self.maturity_phase_text.color = phase_colors.get(phase_key.upper(), ft.Colors.WHITE)

        # 3. Update lane states
        lanes_state = semaphore_data.get("lanes_state", {})
        self.lane_states_panel.update_lanes(semaphore_id, lanes_state)

        # Safe update with protection against closed event loop
        try:
            if self.page:
                self.maturity_phase_text.update()
                self.lane_states_panel.lane_states_column.update()
                if self._current_semaphore_id != getattr(self, "_last_rendered_id", None):
                    self.semaphore_id_text.update()
                    self._last_rendered_id = self._current_semaphore_id
        except (AssertionError, RuntimeError) as e:
            if "Event loop is closed" not in str(e) and "shutdown" not in str(e):
                logging.error(f"[SemaphoreInfoDisplay] Erro inesperado ao atualizar UI: {e}")
        except Exception:
            pass

    def _on_submit(self, e: Any) -> None:
        """Saves a new custom alias for the semaphore."""
        if self._current_semaphore_id:
            self.alias_manager.set_alias(self._current_semaphore_id, self.semaphore_id_text.value)
            if self.page:
                msg = self.locale_manager.get_string(
                    "semaphore_info.msg_saved", default="Nome do semáforo salvo com sucesso!"
                )
                self.page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor="green700")
                self.page.snack_bar.open = True
                self.page.update()
