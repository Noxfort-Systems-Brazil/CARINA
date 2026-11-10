# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Visual component specialized in displaying and copying CCO and EVP endpoints.
Single Responsibility (SRP): visual presentation of remote service URLs.
"""

from typing import Callable, Optional
import flet as ft


class RemoteEndpointsBanner(ft.Container):
    """Stylized banner with CCO and EVP service URLs and dedicated copy/open buttons."""

    def __init__(
        self,
        initial_cco_url: str = "https://<seu-dominio>.ts.net/cco",
        initial_evp_url: str = "https://<seu-dominio>.ts.net/amb/v1",
        initial_local_cco_url: Optional[str] = None,
        on_copy: Optional[Callable[[str, str], None]] = None,
        on_open_url: Optional[Callable[[str], None]] = None,
        **kwargs,
    ):
        super().__init__()
        self.on_copy = on_copy
        self.on_open_url = on_open_url
        self.bgcolor = ft.Colors.with_opacity(0.08, ft.Colors.CYAN)
        self.border = ft.border.all(1, ft.Colors.with_opacity(0.25, ft.Colors.CYAN))
        self.border_radius = 8
        self.padding = 14

        self.cco_path_text = ft.Text(initial_cco_url, color=ft.Colors.CYAN_300, size=12, weight=ft.FontWeight.W_500)
        self.evp_path_text = ft.Text(initial_evp_url, color=ft.Colors.AMBER_300, size=12, weight=ft.FontWeight.W_500)

        self.content = ft.Column(
            [
                # Row 1: CCO (Videowall)
                ft.Row(
                    [
                        ft.Icon(ft.Icons.DESKTOP_WINDOWS_ROUNDED, color=ft.Colors.CYAN_400, size=18),
                        ft.Text("🖥️ CCO (Telão / Videowall):", size=13, weight=ft.FontWeight.BOLD),
                        self.cco_path_text,
                        ft.Row(
                            [
                                ft.IconButton(
                                    icon=ft.Icons.OPEN_IN_BROWSER_ROUNDED,
                                    tooltip="Abrir CCO no Navegador",
                                    icon_size=18,
                                    icon_color=ft.Colors.CYAN_300,
                                    on_click=lambda e: self._handle_open_url(self.cco_path_text.value),
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.COPY_ROUNDED,
                                    tooltip="Copiar Link do CCO",
                                    icon_size=16,
                                    on_click=lambda e: self._handle_copy(self.cco_path_text.value, "Link CCO"),
                                ),
                            ],
                            spacing=0,
                        ),
                    ],
                    spacing=8,
                ),
                ft.Divider(height=6, color=ft.Colors.TRANSPARENT),
                # Row 2: EVP (Emergency Vehicles)
                ft.Row(
                    [
                        ft.Icon(ft.Icons.LOCAL_HOSPITAL_ROUNDED, color=ft.Colors.AMBER_400, size=18),
                        ft.Text("🚑 EVP (Viaturas de Emergência):", size=13, weight=ft.FontWeight.BOLD),
                        self.evp_path_text,
                        ft.IconButton(
                            icon=ft.Icons.COPY_ROUNDED,
                            tooltip="Copiar Endpoint EVP",
                            icon_size=16,
                            on_click=lambda e: self._handle_copy(self.evp_path_text.value, "Endpoint EVP"),
                        ),
                    ],
                    spacing=8,
                ),
            ],
            spacing=4,
        )

    def _handle_copy(self, url: str, label: str):
        if self.on_copy:
            self.on_copy(url, label)

    def _handle_open_url(self, url: str):
        if self.on_open_url:
            self.on_open_url(url)
        else:
            try:
                import webbrowser
                webbrowser.open(url)
            except Exception:
                pass

    def update_urls(self, cco_url: str, evp_url: str, *args, **kwargs):
        """Updates endpoint text in container."""
        self.cco_path_text.value = cco_url
        self.evp_path_text.value = evp_url
        if self.page:
            self.update()
