# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Emergency Vehicle Interactive Details Card.
Displayed upon clicking a vehicle marker (Triangle, Square, Circle) on the map.
"""

from typing import Any, Callable, Dict, Optional
import flet as ft


class EVPVehicleCard(ft.Card):
    """
    Floating/modal card displaying real-time telemetry of the selected vehicle.
    """

    def __init__(self, on_close: Optional[Callable[[], None]] = None):
        super().__init__()
        self.on_close = on_close
        self.visible = False
        self.elevation = 8

        self.lbl_title = ft.Text("Viatura", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
        self.lbl_corp = ft.Text("Corporação", size=13, color=ft.Colors.BLUE_GREY_200)
        self.lbl_speed = ft.Text("0.0 km/h", size=14, weight=ft.FontWeight.W_500)
        self.lbl_heading = ft.Text("0°", size=14)
        self.badge_siren = ft.Container(
            content=ft.Text("PATRULHA", size=12, weight=ft.FontWeight.BOLD),
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
            border_radius=4,
            bgcolor=ft.Colors.BLUE_GREY_700,
        )

        self.content = ft.Container(
            padding=16,
            width=280,
            bgcolor=ft.Colors.BLUE_GREY_900,
            border_radius=8,
            content=ft.Column(
                tight=True,
                spacing=8,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            self.lbl_title,
                            ft.IconButton(
                                icon=ft.Icons.CLOSE_ROUNDED,
                                icon_size=18,
                                on_click=self._handle_close,
                                tooltip="Fechar",
                            ),
                        ],
                    ),
                    self.lbl_corp,
                    ft.Divider(height=1, color=ft.Colors.BLUE_GREY_700),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text("Velocidade:", size=13, color=ft.Colors.GREY_400),
                            self.lbl_speed,
                        ],
                    ),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text("Rumo (Bússola):", size=13, color=ft.Colors.GREY_400),
                            self.lbl_heading,
                        ],
                    ),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text("Status:", size=13, color=ft.Colors.GREY_400),
                            self.badge_siren,
                        ],
                    ),
                ],
            ),
        )

    def display_vehicle(self, data: Dict[str, Any]) -> None:
        """Updates and displays the card with vehicle data."""
        v_id = data.get("vehicle_id", "DESCONHECIDO")
        corp = data.get("corporation", "POLICIA")
        speed = data.get("speed_kmh", 0.0)
        heading = data.get("heading_deg", 0.0)
        siren = data.get("siren_active", False)

        self.lbl_title.value = f"🚨 {v_id}"
        self.lbl_corp.value = f"Corporação: {corp}"
        self.lbl_speed.value = f"{speed:.1f} km/h"
        self.lbl_heading.value = f"{heading:.0f}°"

        if siren:
            self.badge_siren.content.value = "EMERGÊNCIA ATIVA"
            self.badge_siren.bgcolor = ft.Colors.RED_700
        else:
            self.badge_siren.content.value = "PATRULHA"
            self.badge_siren.bgcolor = ft.Colors.BLUE_GREY_700

        self.visible = True
        self.update()

    def _handle_close(self, e):
        self.visible = False
        self.update()
        if self.on_close:
            self.on_close()
