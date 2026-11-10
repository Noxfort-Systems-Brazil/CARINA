# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import flet as ft

from ui.handlers.locale_manager import LocaleManager


class PlanningCommandBarWidget(ft.Container):
    """
    Widget responsible for the bottom planning command bar (action buttons and status indicator).
    """

    def __init__(self, on_analyze_click=None, on_save_report_click=None, locale_manager: LocaleManager = None):
        super().__init__(
            height=60,
            padding=ft.padding.symmetric(horizontal=20),
            border_radius=ft.border_radius.only(top_left=10, top_right=10),
            bgcolor=ft.Colors.WHITE10,
        )

        self.locale_manager = locale_manager
        self.analyze_button = ft.ElevatedButton("", disabled=True, on_click=on_analyze_click)
        self.save_report_button = ft.ElevatedButton(
            "", icon=ft.Icons.SAVE_ALT_ROUNDED, on_click=on_save_report_click, disabled=True
        )
        self.status_text = ft.Text("", italic=True)

        self.content = ft.Row(
            controls=[
                self.analyze_button,
                ft.Container(expand=True),
                self.status_text,
                ft.Container(expand=True),
                self.save_report_button,
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        if locale_manager:
            self.update_translations(locale_manager)
        else:
            try:
                self.update_translations(LocaleManager())
            except Exception:
                pass

    def set_status(self, text: str, italic: bool = False, color=None):
        self.status_text.value = text
        self.status_text.italic = italic
        self.status_text.color = color

    def update_translations(self, lm: LocaleManager, is_analyzing: bool = False):
        if not lm:
            return
        self.locale_manager = lm
        self.analyze_button.text = lm.get_string("planning_view.analyze_button", "Analisar Infraestrutura")
        self.analyze_button.tooltip = lm.get_string(
            "planning_view.analyze_tooltip", "Carrega o último relatório de infraestrutura gerado pelo sistema"
        )
        self.save_report_button.text = lm.get_string("planning_view.generate_report_button", "Salvar Relatório (.docx)")
        if not is_analyzing and not self.analyze_button.disabled:
            self.status_text.value = lm.get_string(
                "planning_view.status_ready", "Pronto para carregar a última análise."
            )
        elif not self.status_text.value or self.analyze_button.disabled:
            self.status_text.value = lm.get_string(
                "planning_view.status_loading", "Aguardando carregamento da topologia do mapa..."
            )
        if self.page:
            self.update()
