# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: ui/components/hardware_status_panel.py
# Author: Gabriel Moraes
# Date: September 2026

from typing import Dict, Optional

import flet as ft

from ui.handlers.locale_manager import LocaleManager


class HardwareStatusPanel(ft.Container):
    """
    Subcomponent that displays controller hardware brand, model, and connectivity status.
    Follows Single Responsibility Principle (SRP).
    """

    def __init__(self, locale_manager: LocaleManager):
        super().__init__()
        self.locale_manager = locale_manager

        self.hardware_brand_label = ft.Text("Marca:", size=11, color=ft.Colors.WHITE54)
        self.hardware_brand_text = ft.Text(
            "Desconectado",
            weight=ft.FontWeight.BOLD,
            size=12,
            color=ft.Colors.CYAN_200,
            overflow=ft.TextOverflow.ELLIPSIS,
            max_lines=1,
            tooltip="Desconectado",
        )
        self.hardware_model_label = ft.Text("Modelo:", size=11, color=ft.Colors.WHITE54)
        self.hardware_model_text = ft.Text(
            "Desconectado",
            weight=ft.FontWeight.BOLD,
            size=12,
            color=ft.Colors.CYAN_200,
            overflow=ft.TextOverflow.ELLIPSIS,
            max_lines=1,
            tooltip="Desconectado",
        )

        self.content = ft.Row(
            controls=[
                ft.Icon(ft.Icons.MEMORY_ROUNDED, color=ft.Colors.CYAN_400, size=22),
                ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                self.hardware_brand_label,
                                ft.Container(content=self.hardware_brand_text, expand=True),
                            ],
                            spacing=4,
                            alignment=ft.MainAxisAlignment.START,
                        ),
                        ft.Row(
                            controls=[
                                self.hardware_model_label,
                                ft.Container(content=self.hardware_model_text, expand=True),
                            ],
                            spacing=4,
                            alignment=ft.MainAxisAlignment.START,
                        ),
                    ],
                    spacing=2,
                    expand=True,
                ),
            ],
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10,
        )
        self.padding = ft.padding.symmetric(horizontal=12, vertical=8)
        self.border = ft.border.all(1, ft.colors.CYAN_900)
        self.border_radius = 8
        self.bgcolor = ft.colors.SURFACE_VARIANT
        self.margin = ft.margin.only(bottom=4)

    def update_translations(self, lm: LocaleManager) -> None:
        self.locale_manager = lm
        self.hardware_brand_label.value = lm.get_string("dashboard_view.hardware_brand_label", default="Marca:")
        self.hardware_model_label.value = lm.get_string("dashboard_view.hardware_model_label", default="Modelo:")

    def update_hardware_info(self, semaphore_id: str, semaphore_data: Dict) -> None:
        """Updates brand and model labels querying hardware status or data payload."""
        not_connected = self.locale_manager.get_string("dashboard_view.not_connected", default="Desconectado")
        not_informed = self.locale_manager.get_string("dashboard_view.not_informed", default="Não informado")

        brand = None
        model = None

        try:
            from src.controller.connection_manager import HardwareConnectionManager

            conn_hw = HardwareConnectionManager.get_global_hardware_info(semaphore_id)
            if conn_hw and conn_hw.get("is_connected"):
                brand = conn_hw.get("brand") or not_informed
                model = conn_hw.get("model") or not_informed
            elif conn_hw:
                brand = not_connected
                model = not_connected
        except Exception:
            pass

        if brand is None:
            if semaphore_data and semaphore_data.get("brand"):
                brand = semaphore_data.get("brand")
                model = semaphore_data.get("model", not_informed)

        if not brand:
            brand = not_connected
            model = not_connected

        self.hardware_brand_text.value = str(brand)
        self.hardware_brand_text.tooltip = str(brand)
        self.hardware_model_text.value = str(model)
        self.hardware_model_text.tooltip = str(model)
