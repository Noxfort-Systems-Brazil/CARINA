# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import flet as ft

from ui.handlers.locale_manager import LocaleManager


class PlanningLegendWidget(ft.Container):
    """
    Widget responsible for rendering and internationalizing the planning map legend.
    """

    def __init__(self, locale_manager: LocaleManager = None):
        super().__init__(padding=ft.padding.symmetric(vertical=5))

        self.legend_title = ft.Text(weight=ft.FontWeight.BOLD)
        self.legend_tl_keep = ft.Text()
        self.legend_tl_remove = ft.Text()
        self.legend_tl_add = ft.Text()
        self.legend_junction = ft.Text()
        self.legend_street = ft.Text()

        self.content = ft.Row(
            controls=[
                self.legend_title,
                ft.Icon(ft.Icons.SQUARE, color=ft.Colors.BLUE_800, size=16),
                self.legend_tl_keep,
                ft.Icon(ft.Icons.SQUARE, color=ft.Colors.RED_700, size=16),
                self.legend_tl_remove,
                ft.Icon(ft.Icons.SQUARE, color=ft.Colors.GREEN_700, size=16),
                self.legend_tl_add,
                ft.Icon(ft.Icons.CIRCLE, color=ft.Colors.ORANGE_600, size=16),
                self.legend_junction,
                ft.Container(width=20, height=4, bgcolor=ft.Colors.BLACK, border_radius=2),
                self.legend_street,
            ],
            alignment=ft.MainAxisAlignment.CENTER,
        )

        if locale_manager:
            self.update_translations(locale_manager)
        else:
            try:
                self.update_translations(LocaleManager())
            except Exception:
                pass

    def update_translations(self, lm: LocaleManager):
        if not lm:
            return
        self.legend_title.value = lm.get_string("planning_view.legend_title", "Legenda:")
        self.legend_tl_keep.value = lm.get_string("planning_view.legend_tl_keep", "Manter")
        self.legend_tl_remove.value = lm.get_string("planning_view.legend_tl_remove", "Tirar")
        self.legend_tl_add.value = lm.get_string("planning_view.legend_tl_add", "Por")
        self.legend_junction.value = lm.get_string("planning_view.legend_junction", "Cruzamento")
        self.legend_street.value = lm.get_string("planning_view.legend_street", "Vias")
        if self.page:
            self.update()
