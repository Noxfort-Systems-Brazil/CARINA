# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
EVP Vehicle Manual Registration Modal Dialog.
Follows the Single Responsibility Principle (SRP), encapsulating the form,
input fields, and basic UI validation.
"""

from typing import Any, Callable, Dict, Optional
import flet as ft


class EVPVehicleDialog:
    """
    Manages the modal dialog for manual emergency vehicle registration.
    """

    def __init__(self, on_save: Optional[Callable[[Dict[str, Any]], None]] = None):
        self.on_save = on_save
        self.page: Optional[ft.Page] = None

        # Form fields
        self.txt_veh_id = ft.TextField(
            label="Identificador da Viatura *",
            hint_text="Ex: SAMU-01, BOMBEIRO-01, POLICIA-01",
            autofocus=True,
            width=260,
        )
        self.dd_corp = ft.Dropdown(
            label="Corporação *",
            value="SAMU",
            options=[
                ft.dropdown.Option("SAMU", "SAMU (Ambulância / Resgate)"),
                ft.dropdown.Option("BOMBEIRO", "Corpo de Bombeiros"),
                ft.dropdown.Option("POLICIA", "Polícia Militar / Trânsito"),
            ],
            width=260,
        )
        self.txt_plate = ft.TextField(
            label="Placa do Veículo",
            hint_text="Ex: BRA2E19, SAM-1920",
            width=260,
        )
        self.txt_ip = ft.TextField(
            label="Endereço IP / Host",
            value="10.8.0.15",
            width=260,
        )
        self.txt_port = ft.TextField(
            label="Porta",
            value="8085",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=120,
        )
        self.dd_proto = ft.Dropdown(
            label="Protocolo",
            value="HTTP",
            options=[
                ft.dropdown.Option("HTTP"),
                ft.dropdown.Option("UDP"),
                ft.dropdown.Option("MQTT"),
            ],
            width=120,
        )
        self.txt_device_id = ft.TextField(
            label="Token / Device ID / IMEI",
            hint_text="Ex: IMEI-864209041234567",
            width=260,
        )
        self.txt_auth_token = ft.TextField(
            label="Chave Secreta / Auth Token",
            hint_text="Ex: sec_token_01",
            password=True,
            can_reveal_password=True,
            width=260,
        )
        self.txt_desc = ft.TextField(
            label="Descrição / Detalhes",
            hint_text="Ex: Ambulância UTI Móvel de Suporte Avançado",
            width=540,
        )

        # AlertDialog dialog
        self.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.ADD_MODERATOR_ROUNDED, color=ft.Colors.BLUE_400),
                    ft.Text("Cadastrar Viatura de Emergência", size=18, weight=ft.FontWeight.BOLD),
                ],
                spacing=8,
            ),
            content=ft.Container(
                width=580,
                content=ft.Column(
                    tight=True,
                    spacing=12,
                    controls=[
                        ft.Text(
                            "Informe os dados de identificação e conexão da viatura autorizada para preempção semafórica.",
                            size=12,
                            color=ft.Colors.GREY_400,
                        ),
                        ft.Row(controls=[self.txt_veh_id, self.dd_corp], spacing=12),
                        ft.Row(controls=[self.txt_plate, self.txt_ip], spacing=12),
                        ft.Row(controls=[self.txt_port, self.dd_proto, self.txt_device_id], spacing=12),
                        ft.Row(controls=[self.txt_auth_token], spacing=12),
                        self.txt_desc,
                    ],
                ),
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=self._handle_cancel),
                ft.ElevatedButton(
                    "Salvar Viatura",
                    icon=ft.Icons.CHECK_ROUNDED,
                    bgcolor=ft.Colors.BLUE_700,
                    color=ft.Colors.WHITE,
                    on_click=self._handle_save,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

    def mount(self, page: ft.Page) -> None:
        """Registers dialog in page overlay."""
        self.page = page
        if self.page and self.dialog not in self.page.overlay:
            self.page.overlay.append(self.dialog)

    def open(self) -> None:
        """Opens dialog and resets fields for new entry."""
        self.txt_veh_id.value = ""
        self.txt_veh_id.error_text = None
        self.txt_plate.value = ""
        self.txt_desc.value = ""
        self.txt_auth_token.value = ""
        self.dialog.open = True
        if self.page:
            self.page.update()

    def close(self) -> None:
        """Closes modal window."""
        self.dialog.open = False
        if self.page:
            self.page.update()

    def _handle_cancel(self, e: Any) -> None:
        self.close()

    def _handle_save(self, e: Any) -> None:
        v_id = (self.txt_veh_id.value or "").strip().upper()
        if not v_id:
            self.txt_veh_id.error_text = "Informe o identificador da viatura"
            if self.page:
                self.page.update()
            return

        port_val = 8085
        try:
            port_val = int(self.txt_port.value or "8085")
        except ValueError:
            port_val = 8085

        data = {
            "vehicle_id": v_id,
            "corporation": self.dd_corp.value or "SAMU",
            "plate": (self.txt_plate.value or "").strip().upper(),
            "ip_address": (self.txt_ip.value or "").strip() or "10.8.0.15",
            "port": port_val,
            "protocol": (self.dd_proto.value or "HTTP").strip().upper(),
            "device_id": (self.txt_device_id.value or "").strip(),
            "auth_token": (self.txt_auth_token.value or "").strip(),
            "description": (self.txt_desc.value or "").strip() or f"Viatura {v_id}",
        }

        self.close()
        if self.on_save:
            self.on_save(data)
