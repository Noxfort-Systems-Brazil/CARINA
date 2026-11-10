# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Any, Dict, List, Optional, Set
import flet as ft

from ui.components.intersection_chips_selector import IntersectionChipsSelector
from ui.handlers.locale_manager import LocaleManager


class YellowScheduleCard(ft.Card):
    """
    Card encapsulating configuration of scheduled flashing yellow traffic lights.
    Complies with Single Responsibility Principle (SRP) and Open/Closed Principle (OCP).
    """

    def __init__(self, initial_values: Dict[str, Any], locale_manager: Optional[LocaleManager] = None):
        super().__init__()
        self.lm = locale_manager
        self._initial_values = initial_values or {}

        # UI Controls
        self.title_icon = ft.Icon(ft.Icons.ACCESS_TIME_ROUNDED, color=ft.Colors.AMBER_400, size=24)
        self.title_text = ft.Text(size=18, weight=ft.FontWeight.BOLD)
        self.desc_text = ft.Text(size=12, color=ft.Colors.WHITE70)

        # Main Switch
        init_enabled = self._initial_values.get("yellow_schedule_enabled", False)
        if isinstance(init_enabled, str):
            init_enabled = init_enabled.strip().lower() in ("true", "1", "yes", "on")
        self.switch_enabled = ft.Switch(value=bool(init_enabled), on_change=self._handle_enabled_toggle)

        # Time Pickers / TextFields
        self.tf_start = ft.TextField(
            value=str(self._initial_values.get("yellow_schedule_start", "23:00")),
            expand=True,
            max_length=5,
            hint_text="23:00",
            on_change=lambda e: self._validate_time_field(self.tf_start),
        )
        self.tf_end = ft.TextField(
            value=str(self._initial_values.get("yellow_schedule_end", "05:00")),
            expand=True,
            max_length=5,
            hint_text="05:00",
            on_change=lambda e: self._validate_time_field(self.tf_end),
        )

        # All Semaphores vs Specific
        init_all = self._initial_values.get("yellow_schedule_all_semaphores", False)
        if isinstance(init_all, str):
            init_all = init_all.strip().lower() in ("true", "1", "yes", "on")
        self.switch_all = ft.Switch(value=bool(init_all), on_change=self._handle_all_toggle)

        # Semaphores list & Chips Component
        init_sem = str(self._initial_values.get("yellow_schedule_semaphores", ""))
        self.tf_semaphores = ft.TextField(
            value=init_sem,
            multiline=False,
            expand=True,
            on_change=self._handle_semaphores_text_change,
        )

        self.chips_selector = IntersectionChipsSelector(
            locale_manager=self.lm,
            on_selection_change=self._on_chips_selection_changed,
        )
        self._parse_selected_ids(init_sem)

        self.semaphores_container = ft.Column(
            controls=[self.tf_semaphores, self.chips_selector],
            spacing=8,
            visible=not self.switch_all.value,
        )

        self.schedule_body = ft.Column(
            controls=[
                ft.Row([self.tf_start, self.tf_end], spacing=15),
                ft.Divider(height=5),
                self.switch_all,
                self.semaphores_container,
            ],
            spacing=12,
            visible=self.switch_enabled.value,
        )

        self.content = ft.Container(
            padding=15,
            content=ft.Column(
                [
                    ft.Row([self.title_icon, self.title_text], spacing=10),
                    self.desc_text,
                    ft.Divider(height=10),
                    self.switch_enabled,
                    self.schedule_body,
                ],
                spacing=10,
            ),
        )

        self._discover_available_intersections()
        if self.lm:
            self.update_translations(self.lm)

    # Backwards-compatible properties and delegates
    @property
    def _known_intersections(self) -> List[str]:
        return self.chips_selector._known_intersections

    @_known_intersections.setter
    def _known_intersections(self, val: List[str]):
        self.chips_selector._known_intersections = val

    @property
    def _selected_ids(self) -> Set[str]:
        return self.chips_selector._selected_ids

    @_selected_ids.setter
    def _selected_ids(self, val: Set[str]):
        self.chips_selector._selected_ids = val

    @property
    def chips_row(self) -> ft.Row:
        return self.chips_selector.chips_row

    @property
    def lbl_chips(self) -> ft.Text:
        return self.chips_selector.lbl_chips

    def _render_chips(self):
        self.chips_selector._render_chips()

    def _toggle_chip(self, sid: str, selected: bool):
        self.chips_selector._toggle_chip(sid, selected)

    def _on_chips_selection_changed(self, selected_ids: Set[str]):
        self.tf_semaphores.value = ", ".join(sorted(list(selected_ids)))
        if self.page:
            self.update()

    def _discover_available_intersections(self):
        try:
            from src.controller.map_discoverer import MapTopologyDiscoverer

            intersections = MapTopologyDiscoverer.discover_intersections()
            if intersections:
                self.set_available_intersections(intersections)
        except Exception:
            pass

    def set_available_intersections(self, intersections: List[str]):
        self.chips_selector.set_available_intersections(intersections)
        if self.page:
            self.update()

    def _parse_selected_ids(self, text: str):
        parsed = {s.strip() for s in text.split(",") if s.strip()}
        self.chips_selector.set_selected_ids(parsed)

    def _handle_semaphores_text_change(self, e):
        self._parse_selected_ids(self.tf_semaphores.value or "")
        if self.page:
            self.update()

    def _handle_enabled_toggle(self, e):
        self.schedule_body.visible = self.switch_enabled.value
        if self.page:
            self.update()

    def _handle_all_toggle(self, e):
        self.semaphores_container.visible = not self.switch_all.value
        if self.page:
            self.update()

    def _validate_time_field(self, tf: ft.TextField) -> bool:
        val = (tf.value or "").strip()
        if not self._is_valid_time(val):
            err_msg = "Formato inválido (HH:MM)"
            if self.lm:
                err_msg = self.lm.get_string("settings_view.yellow_schedule_card.error_time_format", default=err_msg)
            tf.error_text = err_msg
            if self.page:
                self.update()
            return False
        tf.error_text = None
        if self.page:
            self.update()
        return True

    def _validate_start_time(self, e=None) -> bool:
        return self._validate_time_field(self.tf_start)

    def _validate_end_time(self, e=None) -> bool:
        return self._validate_time_field(self.tf_end)

    @staticmethod
    def _is_valid_time(s: str) -> bool:
        if not s or ":" not in s:
            return False
        parts = s.split(":")
        if len(parts) != 2:
            return False
        try:
            h, m = int(parts[0]), int(parts[1])
            return 0 <= h <= 23 and 0 <= m <= 59
        except ValueError:
            return False

    def validate_fields(self) -> bool:
        if not self.switch_enabled.value:
            return True
        return self._validate_time_field(self.tf_start) and self._validate_time_field(self.tf_end)

    def get_values(self) -> Dict[str, Any]:
        return {
            "yellow_schedule_enabled": bool(self.switch_enabled.value),
            "yellow_schedule_start": (self.tf_start.value or "23:00").strip(),
            "yellow_schedule_end": (self.tf_end.value or "05:00").strip(),
            "yellow_schedule_all_semaphores": bool(self.switch_all.value),
            "yellow_schedule_semaphores": (self.tf_semaphores.value or "").strip(),
        }

    def set_values(self, values: Dict[str, Any]):
        enabled = values.get("yellow_schedule_enabled", False)
        if isinstance(enabled, str):
            enabled = enabled.strip().lower() in ("true", "1", "yes", "on")
        self.switch_enabled.value = bool(enabled)
        self.schedule_body.visible = self.switch_enabled.value
        self.tf_start.value = str(values.get("yellow_schedule_start", "23:00"))
        self.tf_end.value = str(values.get("yellow_schedule_end", "05:00"))

        all_sem = values.get("yellow_schedule_all_semaphores", False)
        if isinstance(all_sem, str):
            all_sem = all_sem.strip().lower() in ("true", "1", "yes", "on")
        self.switch_all.value = bool(all_sem)
        self.semaphores_container.visible = not self.switch_all.value

        sem_str = str(values.get("yellow_schedule_semaphores", ""))
        self.tf_semaphores.value = sem_str
        self._parse_selected_ids(sem_str)
        if self.page:
            self.update()

    def update_translations(self, lm: LocaleManager):
        self.lm = lm
        self.title_text.value = lm.get_string("settings_view.yellow_schedule_card.title")
        self.desc_text.value = lm.get_string("settings_view.yellow_schedule_card.description")
        self.switch_enabled.label = lm.get_string("settings_view.yellow_schedule_card.enable_switch")
        self.tf_start.label = lm.get_string("settings_view.yellow_schedule_card.start_time_label")
        self.tf_start.hint_text = lm.get_string("settings_view.yellow_schedule_card.start_time_hint", default="ex: 23:00")
        self.tf_end.label = lm.get_string("settings_view.yellow_schedule_card.end_time_label")
        self.tf_end.hint_text = lm.get_string("settings_view.yellow_schedule_card.end_time_hint", default="ex: 05:00")
        self.switch_all.label = lm.get_string("settings_view.yellow_schedule_card.all_semaphores_switch")
        self.tf_semaphores.label = lm.get_string("settings_view.yellow_schedule_card.target_semaphores_label")
        self.tf_semaphores.hint_text = lm.get_string("settings_view.yellow_schedule_card.target_semaphores_hint", default="ex: J1, J2, J5")
        self.chips_selector.update_translations(lm)
        if self.page:
            self.update()
