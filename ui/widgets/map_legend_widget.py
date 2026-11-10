# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Defines the MapLegendWidget.
"""

import os

import flet as ft

# --- CHANGE 1: Import LocaleManager ---
from ui.handlers.locale_manager import LocaleManager


class MapLegendWidget(ft.Container):
    """
    A floating panel that displays the map legend.
    """

    def __init__(self, locale_manager: LocaleManager):
        super().__init__(left=10, top=10)

        # --- CHANGE 2: Store LocaleManager and refactor text controls ---
        self.locale_manager = locale_manager

        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

        def get_asset_path(icon_name: str) -> str:
            return os.path.join(project_root, "ui", "assets", icon_name)

        # Text controls are now class attributes to be updatable
        self.text_existing = ft.Text(size=12)
        self.text_add = ft.Text(size=12)
        self.text_remove = ft.Text(size=12)

        legend_items = [
            ft.Row(
                controls=[ft.Image(src=get_asset_path("icon_existing.png"), width=24, height=24), self.text_existing],
                spacing=10,
            ),
            ft.Row(
                controls=[ft.Image(src=get_asset_path("icon_add.png"), width=24, height=24), self.text_add], spacing=10
            ),
            ft.Row(
                controls=[ft.Image(src=get_asset_path("icon_remove.png"), width=24, height=24), self.text_remove],
                spacing=10,
            ),
        ]

        legend_content = ft.Column(controls=legend_items, spacing=8)

        # Main container settings
        self.bgcolor = "#A6000000"
        self.border = ft.border.all(1, ft.Colors.WHITE24)
        self.border_radius = 10
        self.padding = ft.padding.all(10)
        self.content = ft.GestureDetector(
            mouse_cursor=ft.MouseCursor.MOVE,
            drag_interval=10,
            on_pan_update=self._pan_update,
            content=legend_content,
        )

    def did_mount(self):
        """Called when the widget is mounted on the page."""
        self.update_translations(self.locale_manager)

    # --- CHANGE 3: New method to translate the widget ---
    def update_translations(self, lm: LocaleManager):
        """Updates the texts of this widget based on LocaleManager."""
        self.text_existing.value = lm.get_string("planning_view.legend_existing")
        self.text_add.value = lm.get_string("planning_view.legend_add")
        self.text_remove.value = lm.get_string("planning_view.legend_remove")
        if self.page:
            self.update()

    def _pan_update(self, e: ft.DragUpdateEvent):
        """
        Updates the legend position and constrains it within parent container bounds.
        """
        new_left = self.left + e.delta_x
        new_top = self.top + e.delta_y

        if self.parent and self.parent.width and self.parent.height:
            margin = 10
            parent_width = self.parent.width
            parent_height = self.parent.height
            self.left = max(margin, min(new_left, parent_width - self.width - margin))
            self.top = max(margin, min(new_top, parent_height - self.height - margin))
        else:
            self.left = new_left
            self.top = new_top

        self.update()
