# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Remote Gateway Form Visual Component and Layout (Clean Architecture / Presentation).
Encapsulates status badges, automatic Tailscale Funnel info, and action buttons for CCO / EVP.
"""

from typing import Any, Callable, Optional

import flet as ft


class RemoteGatewayFormControls:
    """Assembles and manages interface controls and visual states for the Tailscale Remote Gateway."""

    def __init__(
        self,
        is_connected: bool,
        on_test_click: Callable[[Any], None],
        on_connect_click: Callable[[Any], None],
        on_disconnect_click: Callable[[Any], None],
        initial_domain: str = "",
    ):
        self.title_text = ft.Text(
            "Gateway Remoto & Acesso Externo (Tailscale)",
            size=18,
            weight=ft.FontWeight.BOLD,
        )
        self.status_icon = ft.Icon(
            name=ft.Icons.RADIO_BUTTON_CHECKED if is_connected else ft.Icons.RADIO_BUTTON_UNCHECKED,
            color=ft.Colors.GREEN_500 if is_connected else ft.Colors.RED_500,
            size=16,
        )
        self.status_text = ft.Text(
            "ONLINE" if is_connected else "DESCONECTADO",
            weight=ft.FontWeight.W_500,
            color=ft.Colors.GREEN_500 if is_connected else ft.Colors.RED_500,
        )
        self.status_display = ft.Row([self.status_icon, self.status_text], alignment=ft.MainAxisAlignment.START)

        self.info_text = ft.Text(
            "Túnel HTTPS Zero-Trust gerenciado automaticamente no backend via Tailscale Funnel (porta 2201).",
            size=12,
            color=ft.Colors.GREY_300,
        )

        self.btn_test = ft.OutlinedButton(
            text="Verificar Status Tailscale",
            icon=ft.Icons.WIFI_FIND_ROUNDED,
            on_click=on_test_click,
        )

        self.btn_connect = ft.ElevatedButton(
            text="Ativar Gateway Tailscale",
            icon=ft.Icons.PLAY_ARROW_ROUNDED,
            bgcolor=ft.Colors.GREEN_700,
            color=ft.Colors.WHITE,
            on_click=on_connect_click,
            visible=not is_connected,
        )

        self.btn_disconnect = ft.ElevatedButton(
            text="Desativar Gateway",
            icon=ft.Icons.POWER_SETTINGS_NEW_ROUNDED,
            bgcolor=ft.Colors.RED_700,
            color=ft.Colors.WHITE,
            on_click=on_disconnect_click,
            visible=is_connected,
        )

    def build_layout(self, banner_control: ft.Control) -> ft.Container:
        """Structures layout in a responsive container."""
        return ft.Container(
            padding=18,
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Row([ft.Icon(ft.Icons.PUBLIC, size=24), self.title_text]),
                            self.status_display,
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Text(
                        "Exposição segura e automática do videowall CCO e ingestão de telemetria de ambulâncias sem configuração de roteador ou CGNAT.",
                        size=12,
                        color=ft.Colors.GREY_400,
                    ),
                    ft.Divider(),
                    banner_control,
                    ft.Container(
                        padding=ft.padding.symmetric(vertical=6, horizontal=10),
                        bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.WHITE),
                        border_radius=6,
                        content=ft.Row(
                            [
                                ft.Icon(ft.Icons.SHIELD_OUTLINED, color=ft.Colors.GREEN_400, size=18),
                                self.info_text,
                            ],
                            spacing=8,
                        ),
                    ),
                    ft.Row(
                        [
                            self.btn_test,
                            ft.Row([self.btn_connect, self.btn_disconnect]),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                ],
                spacing=12,
            ),
        )

    def apply_connection_state(self, is_connected: bool) -> None:
        """Synchronizes visibility and enablement of visual controls."""
        self.btn_connect.visible = not is_connected
        self.btn_disconnect.visible = is_connected

        self.status_icon.name = (
            ft.Icons.RADIO_BUTTON_CHECKED if is_connected else ft.Icons.RADIO_BUTTON_UNCHECKED
        )
        self.status_icon.color = ft.Colors.GREEN_500 if is_connected else ft.Colors.RED_500
        self.status_text.value = "ONLINE" if is_connected else "DESCONECTADO"
        self.status_text.color = ft.Colors.GREEN_500 if is_connected else ft.Colors.RED_500
