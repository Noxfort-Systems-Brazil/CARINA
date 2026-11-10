# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
EVP Safety Parameters and CONTRAN Regulations Card.
Allows configuring the dwell watchdog, block entry thresholds,
and displays vehicle shape and color conventions.
"""

from typing import Any
import flet as ft

from src.evp.evp_service import EVPService


class EVPSafetyParametersCard(ft.Card):
    """
    CONTRAN Road Parameters Card in the EVP settings tab.
    """

    def __init__(self, locale_manager: Any = None):
        super().__init__()
        self.elevation = 2
        self.expand = True
        self.locale_manager = locale_manager
        self.evp_service = EVPService.get_instance()

        self.txt_watchdog = ft.TextField(
            label="Watchdog Máximo Dwell (segundos)",
            value=str(int(self.evp_service.max_dwell_timeout_seconds)),
            width=260,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        self.txt_entry_min = ft.TextField(
            label="Início da Quadra - Distância Mínima (m)",
            value=str(int(self.evp_service.kinematics.block_entry_min_meters)),
            width=260,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        self.txt_entry_max = ft.TextField(
            label="Início da Quadra - Distância Máxima (m)",
            value=str(int(self.evp_service.kinematics.block_entry_max_meters)),
            width=260,
            keyboard_type=ft.KeyboardType.NUMBER,
        )

        self._build_layout()

    def _build_layout(self):
        legend_row = ft.Row(
            spacing=25,
            wrap=True,
            controls=[
                self._build_legend_item("▲ Triângulo", "SAMU / Resgate", "#FFFFFF", "#E53935"),
                self._build_legend_item("■ Quadrado", "Bombeiros", "#FF9800", "#FF3D00"),
                self._build_legend_item("● Círculo", "Polícia / Trânsito", "#1E3A8A", "#2563EB"),
            ],
        )

        params_row = ft.Row(
            spacing=16,
            wrap=True,
            controls=[
                self.txt_watchdog,
                self.txt_entry_min,
                self.txt_entry_max,
            ],
        )

        btn_save = ft.ElevatedButton(
            "Salvar Parâmetros CONTRAN",
            icon=ft.Icons.SAVE_ROUNDED,
            bgcolor=ft.Colors.BLUE_700,
            color=ft.Colors.WHITE,
            on_click=self._save_parameters,
        )

        self.content = ft.Container(
            padding=16,
            expand=True,
            content=ft.Column(
                spacing=14,
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.SECURITY_ROUNDED, color=ft.Colors.BLUE_400),
                            ft.Text("Parâmetros de Segurança e Regulamentação CONTRAN", size=18, weight=ft.FontWeight.BOLD),
                        ]
                    ),
                    ft.Text(
                        "Configuração dos limites de retenção semafórica (Dwell Hold) e convenção geométrica de identificação visual.",
                        size=12,
                        color=ft.Colors.GREY_400,
                    ),
                    legend_row,
                    ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                    params_row,
                ],
            ),
        )

    def _build_legend_item(self, shape_text: str, label: str, base_color: str, alert_color: str) -> ft.Control:
        return ft.Row(
            spacing=8,
            controls=[
                ft.Container(width=16, height=16, bgcolor=base_color, border_radius=3),
                ft.Container(width=16, height=16, bgcolor=alert_color, border_radius=3),
                ft.Column(
                    spacing=1,
                    controls=[
                        ft.Text(shape_text, weight=ft.FontWeight.BOLD, size=13),
                        ft.Text(label, size=11, color=ft.Colors.GREY_400),
                    ],
                ),
            ],
        )

    def get_values(self) -> dict:
        return {
            "evp_max_dwell": self.txt_watchdog.value,
            "evp_block_min": self.txt_entry_min.value,
            "evp_block_max": self.txt_entry_max.value,
        }

    def set_values(self, values: dict):
        self.txt_watchdog.value = str(values.get("evp_max_dwell", int(self.evp_service.max_dwell_timeout_seconds)))
        self.txt_entry_min.value = str(values.get("evp_block_min", int(self.evp_service.kinematics.block_entry_min_meters)))
        self.txt_entry_max.value = str(values.get("evp_block_max", int(self.evp_service.kinematics.block_entry_max_meters)))
        if self.page:
            self.update()

    def has_unsaved_changes(self) -> bool:
        try:
            wd = float(self.txt_watchdog.value)
            e_min = float(self.txt_entry_min.value)
            e_max = float(self.txt_entry_max.value)
            return (
                abs(wd - self.evp_service.max_dwell_timeout_seconds) > 1e-3
                or abs(e_min - self.evp_service.kinematics.block_entry_min_meters) > 1e-3
                or abs(e_max - self.evp_service.kinematics.block_entry_max_meters) > 1e-3
            )
        except (ValueError, TypeError):
            return True

    def save_changes(self) -> bool:
        try:
            wd = float(self.txt_watchdog.value)
            e_min = float(self.txt_entry_min.value)
            e_max = float(self.txt_entry_max.value)
            self.evp_service.max_dwell_timeout_seconds = wd
            self.evp_service.kinematics.block_entry_min_meters = e_min
            self.evp_service.kinematics.block_entry_max_meters = e_max
            return True
        except ValueError:
            return False

    def discard_changes(self) -> None:
        self.txt_watchdog.value = str(int(self.evp_service.max_dwell_timeout_seconds))
        self.txt_entry_min.value = str(int(self.evp_service.kinematics.block_entry_min_meters))
        self.txt_entry_max.value = str(int(self.evp_service.kinematics.block_entry_max_meters))
        if self.page:
            self.update()

