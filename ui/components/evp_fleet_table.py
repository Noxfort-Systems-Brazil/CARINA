# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Emergency Vehicle Preemption (EVP) Fleet Table Visual Component.
Follows the Single Responsibility Principle (SRP), encapsulating row building,
connectivity chip formatting, and empty table state representation.
"""

from typing import Any, Callable, Dict, List, Optional
import flet as ft


class EVPFleetTable(ft.Container):
    """
    Subcomponent rendering the vehicles table and real-time status chips.
    """

    def __init__(self, on_delete: Optional[Callable[[str], None]] = None):
        super().__init__()
        self.expand = True
        self.on_delete = on_delete

        self.col_id = ft.Text("Viatura", weight=ft.FontWeight.BOLD)
        self.col_plate = ft.Text("Placa", weight=ft.FontWeight.BOLD)
        self.col_endpoint = ft.Text("Endereço IP / Porta", weight=ft.FontWeight.BOLD)
        self.col_proto = ft.Text("Protocolo", weight=ft.FontWeight.BOLD)
        self.col_auth = ft.Text("Token / Device ID", weight=ft.FontWeight.BOLD)
        self.col_status = ft.Text("Status", weight=ft.FontWeight.BOLD)
        self.col_actions = ft.Text("Ações", weight=ft.FontWeight.BOLD)

        self.table = ft.DataTable(
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=8,
            heading_row_color=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            horizontal_margin=16,
            column_spacing=24,
            columns=[
                ft.DataColumn(self.col_id),
                ft.DataColumn(self.col_plate),
                ft.DataColumn(self.col_endpoint),
                ft.DataColumn(self.col_proto),
                ft.DataColumn(self.col_auth),
                ft.DataColumn(self.col_status),
                ft.DataColumn(self.col_actions),
            ],
            rows=[],
        )

        self.empty_state_container = ft.Container(
            visible=False,
            padding=32,
            alignment=ft.alignment.center,
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
                controls=[
                    ft.Icon(ft.Icons.DIRECTIONS_CAR_ROUNDED, size=48, color=ft.Colors.GREY_500),
                    ft.Text("Nenhuma viatura cadastrada no momento.", size=15, weight=ft.FontWeight.W_500, color=ft.Colors.GREY_300),
                    ft.Text("Cadastre manualmente pelo botão acima ou importe uma planilha via CSV.", size=12, color=ft.Colors.GREY_500),
                ],
            ),
        )

        self.content = ft.Column(
            expand=True,
            scroll=ft.ScrollMode.ADAPTIVE,
            controls=[
                self.empty_state_container,
                ft.Row(controls=[self.table], scroll=ft.ScrollMode.ADAPTIVE, expand=True),
            ],
        )

    def set_vehicles(self, vehicles: List[Dict[str, Any]]) -> None:
        """Updates table records with the provided vehicle list."""
        self.table.rows = [self._build_row(v) for v in vehicles]
        has_items = bool(vehicles)
        self.table.visible = has_items
        self.empty_state_container.visible = not has_items

    def _build_status_chip(self, is_online: bool, siren: bool, last_seen: float) -> ft.Container:
        """Renders visual status badge for vehicular antenna connection."""
        if is_online:
            return ft.Container(
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                bgcolor=ft.Colors.GREEN_900,
                border=ft.border.all(1, ft.Colors.GREEN_400),
                border_radius=4,
                tooltip="Viatura conectada e transmitindo telemetria GPS em tempo real.",
                content=ft.Row(
                    spacing=4,
                    tight=True,
                    controls=[
                        ft.Container(width=6, height=6, bgcolor=ft.Colors.GREEN_400, border_radius=3),
                        ft.Text(
                            "ONLINE (Sirene)" if siren else "ONLINE",
                            size=11,
                            color=ft.Colors.GREEN_100,
                            weight=ft.FontWeight.BOLD,
                        ),
                    ],
                ),
            )

        txt_seen = "Desligada" if last_seen < 0 else f"Off ({last_seen:.0f}s)"
        tooltip_txt = (
            "Viatura autorizada e cadastrada. Aguardando transmissão de telemetria GPS na porta 8085 (/api/v1/evp/telemetry)."
            if last_seen < 0
            else f"Viatura sem transmissão de sinal GPS há {last_seen:.0f} segundos."
        )
        return ft.Container(
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
            bgcolor=ft.Colors.BLUE_GREY_800,
            border=ft.border.all(1, ft.Colors.GREY_600),
            border_radius=4,
            tooltip=tooltip_txt,
            content=ft.Row(
                spacing=4,
                tight=True,
                controls=[
                    ft.Container(width=6, height=6, bgcolor=ft.Colors.GREY_500, border_radius=3),
                    ft.Text(txt_seen, size=11, color=ft.Colors.GREY_300),
                ],
            ),
        )

    def _build_row(self, v: Dict[str, Any]) -> ft.DataRow:
        """Constructs an individual table row for the vehicle."""
        v_id = v.get("vehicle_id", "")
        corp = v.get("corporation", "")
        plate = v.get("plate", "-") or "-"
        ip = v.get("ip_address", "10.8.0.x") or "10.8.0.x"
        port = v.get("port", 8085)
        proto = v.get("protocol", "HTTP") or "HTTP"
        auth = v.get("device_id") or v.get("auth_token") or "IMEI-Ativo"
        is_online = bool(v.get("is_online", False))
        siren = bool(v.get("siren_active", False))
        last_seen = v.get("last_seen_seconds", -1.0)

        status_chip = self._build_status_chip(is_online, siren, last_seen)

        delete_btn = ft.IconButton(
            icon=ft.Icons.DELETE_OUTLINE_ROUNDED,
            icon_color=ft.Colors.RED_400,
            tooltip=f"Remover {v_id}",
            on_click=lambda _, vid=v_id: self.on_delete(vid) if self.on_delete else None,
        )

        return ft.DataRow(
            cells=[
                ft.DataCell(
                    ft.Row(
                        spacing=6,
                        tight=True,
                        controls=[
                            ft.Text(f"{v_id}", weight=ft.FontWeight.BOLD),
                            ft.Text(f"({corp})", size=11, color=ft.Colors.GREY_400),
                        ],
                    )
                ),
                ft.DataCell(ft.Text(plate)),
                ft.DataCell(ft.Text(f"{ip}:{port}")),
                ft.DataCell(ft.Text(proto)),
                ft.DataCell(ft.Text(auth, size=11, color=ft.Colors.GREY_400)),
                ft.DataCell(status_chip),
                ft.DataCell(delete_btn),
            ]
        )
