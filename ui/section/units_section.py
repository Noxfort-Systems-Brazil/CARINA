# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Any, Dict

import flet as ft

from ui.handlers.locale_manager import LocaleManager


class UnitsSection(ft.Column):
    """
    Sub-widget of ReportFormattingCard managing report measurement units, such as speed.
    """

    def __init__(self, initial_values: Dict[str, Any]):
        super().__init__()
        self.spacing = 15

        self.lbl_units_title = ft.Text(weight=ft.FontWeight.BOLD)
        self.lbl_speed_unit = ft.Text(size=11, weight=ft.FontWeight.W_500)
        self.lbl_decimal_separator = ft.Text(size=11, weight=ft.FontWeight.W_500)

        self.dd_speed_unit = ft.Dropdown(
            options=[
                ft.dropdown.Option("m/s", "m/s"),
                ft.dropdown.Option("km/h", "km/h"),
                ft.dropdown.Option("imperial", "mph (Imperial)"),
            ],
            value=initial_values.get("xai_speed_unit", "m/s"),
            width=200,
        )

        self.dd_decimal_separator = ft.Dropdown(
            options=[
                ft.dropdown.Option(",", "Vírgula Decimal (1,23)"),
                ft.dropdown.Option(".", "Ponto Decimal (1.23)"),
            ],
            value=initial_values.get("decimal_separator", ","),
            width=220,
        )

        self.controls = [
            self.lbl_units_title,
            ft.Row(
                controls=[
                    ft.Column([self.lbl_speed_unit, self.dd_speed_unit]),
                    ft.Column([self.lbl_decimal_separator, self.dd_decimal_separator]),
                ],
                spacing=20,
                alignment=ft.MainAxisAlignment.START,
            ),
        ]

    def get_values(self) -> Dict[str, Any]:
        return {
            "xai_speed_unit": self.dd_speed_unit.value,
            "decimal_separator": self.dd_decimal_separator.value,
        }

    def set_values(self, values: Dict[str, Any]):
        self.dd_speed_unit.value = values.get("xai_speed_unit", "m/s")
        self.dd_decimal_separator.value = values.get("decimal_separator", ",")

    def update_translations(self, lm: LocaleManager):
        self.lbl_units_title.value = lm.get_string(
            "settings_view.formatting_card.units_title", default="Unidades de Medida do Relatório"
        )
        self.lbl_speed_unit.value = lm.get_string(
            "settings_view.formatting_card.speed_unit_label", default="Unidade de Velocidade"
        )
        self.lbl_decimal_separator.value = lm.get_string(
            "settings_view.formatting_card.decimal_separator_label", default="Separador Decimal"
        )

        if len(self.dd_speed_unit.options) >= 3:
            self.dd_speed_unit.options[2].text = lm.get_string(
                "settings_view.formatting_card.speed_unit_imperial", default="mph (Imperial)"
            )

        if len(self.dd_decimal_separator.options) >= 2:
            self.dd_decimal_separator.options[0].text = lm.get_string(
                "settings_view.formatting_card.decimal_separator_comma", default="Vírgula Decimal (1,23)"
            )
            self.dd_decimal_separator.options[1].text = lm.get_string(
                "settings_view.formatting_card.decimal_separator_dot", default="Ponto Decimal (1.23)"
            )
