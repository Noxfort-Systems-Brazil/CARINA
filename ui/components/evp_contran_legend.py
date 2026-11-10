# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
CONTRAN Geometric Legend Component (UI / Presentation / SOLID: SRP).
Renders the visual informative legend for CONTRAN geometric conventions and colors.
"""

import flet as ft


class EVPContranLegend(ft.Container):
    """Visual informative legend for CONTRAN geometric conventions and colors."""

    def __init__(self):
        super().__init__(
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            border_radius=8,
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            content=ft.Row(
                spacing=24,
                wrap=True,
                controls=[
                    ft.Text("Convenção CONTRAN:", weight=ft.FontWeight.BOLD, size=12, color=ft.Colors.BLUE_300),
                    self._build_legend_item("▲ Triângulo", "SAMU / Resgate", "#FFFFFF", "#E53935"),
                    self._build_legend_item("■ Quadrado", "Bombeiros", "#FF9800", "#FF3D00"),
                    self._build_legend_item("● Círculo", "Polícia / Trânsito", "#1E3A8A", "#2563EB"),
                ],
            ),
        )

    @staticmethod
    def _build_legend_item(shape_text: str, label: str, base_color: str, alert_color: str) -> ft.Control:
        return ft.Row(
            spacing=6,
            tight=True,
            controls=[
                ft.Container(width=12, height=12, bgcolor=base_color, border_radius=2),
                ft.Container(width=12, height=12, bgcolor=alert_color, border_radius=2),
                ft.Text(f"{shape_text} ({label})", size=11, color=ft.Colors.GREY_300),
            ],
        )
