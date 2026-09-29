# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: ui/components/lane_states_panel.py
# Author: Gabriel Moraes
# Date: September 2026

from typing import Any, Callable, Dict, Optional

import flet as ft

from ui.handlers.locale_manager import LocaleManager
from ui.managers.alias_manager import AliasManager


class LaneStatesPanel(ft.Column):
    """
    Subcomponent displaying the individual lanes, status lamp indicators, and lane aliases.
    Follows Single Responsibility Principle (SRP).
    """

    STATE_COLORS = {
        "G": ft.Colors.GREEN_ACCENT_700,
        "g": ft.Colors.GREEN_ACCENT_700,
        "Y": ft.Colors.AMBER_ACCENT_700,
        "y": ft.Colors.AMBER_ACCENT_700,
        "s": ft.Colors.AMBER_ACCENT_700,
        "R": ft.Colors.RED_ACCENT_700,
        "r": ft.Colors.RED_ACCENT_700,
        "u": ft.Colors.RED_ACCENT_700,
        "o": ft.Colors.RED_ACCENT_700,
    }

    def __init__(self, locale_manager: LocaleManager, alias_manager: AliasManager):
        super().__init__()
        self.locale_manager = locale_manager
        self.alias_manager = alias_manager
        self._current_semaphore_id: Optional[str] = None
        self._lane_controls_map: Dict[str, ft.Container] = {}

        self.lane_states_title = ft.Text(weight=ft.FontWeight.BOLD)
        self.lane_states_column = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, spacing=4)
        self.lane_states_container = ft.Container(
            content=self.lane_states_column,
            height=120,
            border=ft.border.all(1, ft.Colors.WHITE12),
            border_radius=5,
            padding=ft.padding.all(8),
        )

        self.controls = [self.lane_states_title, self.lane_states_container]
        self.spacing = 4

    def update_translations(self, lm: LocaleManager) -> None:
        self.locale_manager = lm
        self.lane_states_title.value = lm.get_string("dashboard_view.lane_states_title")
        for control in self.lane_states_column.controls:
            if isinstance(control, ft.Text):
                control.value = lm.get_string("lane_states.no_data", default="Nenhum dado de via disponível.")
            elif isinstance(control, ft.Row):
                for c in control.controls:
                    if isinstance(c, ft.TextField):
                        c.tooltip = lm.get_string("lane_states.rename_tooltip", default="Clique para renomear")
        if self.page:
            self.update()

    def update_lanes(self, semaphore_id: str, lanes_state: Dict[str, Any]) -> None:
        """Updates lamp indicators and lane rows based on incoming signal states."""
        if self._current_semaphore_id != semaphore_id:
            self._current_semaphore_id = semaphore_id
            self.lane_states_column.controls.clear()
            self._lane_controls_map.clear()

        if not lanes_state:
            if not self.lane_states_column.controls:
                self.lane_states_column.controls.append(
                    ft.Text(
                        self.locale_manager.get_string("lane_states.no_data", default="Nenhum dado de via disponível."),
                        italic=True,
                        size=12,
                    )
                )
            return

        if len(self.lane_states_column.controls) == 1 and isinstance(self.lane_states_column.controls[0], ft.Text):
            self.lane_states_column.controls.clear()

        for lane_id, state in sorted(lanes_state.items()):
            color = self.STATE_COLORS.get(str(state), ft.Colors.RED_ACCENT_700)

            if lane_id in self._lane_controls_map:
                color_box = self._lane_controls_map[lane_id]
                if color_box.bgcolor != color:
                    color_box.bgcolor = color
                    if self.page:
                        color_box.update()
            else:
                alias = self.alias_manager.get_alias(str(lane_id))
                lane_text = ft.TextField(
                    value=alias,
                    text_size=12,
                    height=28,
                    expand=True,
                    content_padding=ft.padding.only(left=8, right=8),
                    border=ft.InputBorder.OUTLINE,
                    border_color=ft.Colors.WHITE24,
                    bgcolor=ft.Colors.WHITE10,
                    border_radius=4,
                    on_blur=lambda e, lid=str(lane_id): self._on_lane_alias_submit(e, lid),
                    on_submit=lambda e, lid=str(lane_id): self._on_lane_alias_submit(e, lid),
                    tooltip=self.locale_manager.get_string(
                        "lane_states.rename_tooltip", default="Clique para renomear"
                    ),
                )
                color_box = ft.Container(width=14, height=14, bgcolor=color, border_radius=7)
                self._lane_controls_map[lane_id] = color_box

                lane_row = ft.Row(
                    controls=[color_box, lane_text], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=10
                )
                self.lane_states_column.controls.append(lane_row)

    def _on_lane_alias_submit(self, e: Any, lane_id: str) -> None:
        new_alias = e.control.value
        if new_alias:
            self.alias_manager.set_alias(lane_id, new_alias)
        else:
            e.control.value = lane_id
            e.control.update()
            self.alias_manager.set_alias(lane_id, "")

        if self.page:
            msg = self.locale_manager.get_string("lane_states.msg_saved", default="Nome da via salvo com sucesso!")
            self.page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor="green700")
            self.page.snack_bar.open = True
            self.page.update()
