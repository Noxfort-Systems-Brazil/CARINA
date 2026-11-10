# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Callable, List, Optional, Set
import flet as ft

from ui.handlers.locale_manager import LocaleManager


class IntersectionChipsSelector(ft.Column):
    """
    Reusable UI Component for displaying and toggling intersection selection chips.
    Follows Single Responsibility Principle (SRP) by isolating chip interactions.
    """

    def __init__(
        self,
        locale_manager: Optional[LocaleManager] = None,
        on_selection_change: Optional[Callable[[Set[str]], None]] = None,
    ):
        super().__init__(spacing=8)
        self.lm = locale_manager
        self.on_selection_change = on_selection_change

        self._known_intersections: List[str] = []
        self._selected_ids: Set[str] = set()

        self.lbl_chips = ft.Text(size=12, weight=ft.FontWeight.W_500, color=ft.Colors.CYAN_200)
        self.chips_row = ft.Row(wrap=True, spacing=6)

        self.controls = [
            self.lbl_chips,
            self.chips_row,
        ]

        if self.lm:
            self.update_translations(self.lm)

    def set_available_intersections(self, intersections: List[str]):
        """Sets the available intersection IDs for chip rendering."""
        self._known_intersections = sorted(list(set(intersections)))
        self._render_chips()
        if self.page:
            self.update()

    def set_selected_ids(self, ids: Set[str]):
        """Updates the active selection set and refreshes chips."""
        self._selected_ids = set(ids)
        self._render_chips()
        if self.page:
            self.update()

    def get_selected_ids(self) -> Set[str]:
        return set(self._selected_ids)

    def get_selected_string(self) -> str:
        return ", ".join(sorted(list(self._selected_ids)))

    def _render_chips(self):
        self.chips_row.controls.clear()
        for sid in self._known_intersections:
            is_selected = sid in self._selected_ids
            chip = ft.Chip(
                label=ft.Text(sid, size=11),
                selected=is_selected,
                selected_color=ft.Colors.AMBER_700,
                on_select=lambda e, s=sid: self._toggle_chip(s, e.control.selected),
            )
            self.chips_row.controls.append(chip)

    def _toggle_chip(self, sid: str, selected: bool):
        if selected:
            self._selected_ids.add(sid)
        else:
            self._selected_ids.discard(sid)
        self._render_chips()
        if self.on_selection_change:
            self.on_selection_change(self._selected_ids)
        if self.page:
            self.update()

    def update_translations(self, lm: LocaleManager):
        self.lm = lm
        self.lbl_chips.value = lm.get_string("settings_view.yellow_schedule_card.select_chips_label")
        self._render_chips()
        if self.page:
            self.update()
