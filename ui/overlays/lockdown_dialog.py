# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Callable, Optional

import flet as ft


class LockdownDialog:
    """Manages the full-screen emergency lockdown overlay and superuser unlock procedure."""

    def __init__(
        self,
        page: ft.Page,
        control_client,
        locale_manager,
        on_unlocked: Optional[Callable[[str], None]] = None,
    ):
        self.page = page
        self.control_client = control_client
        self.locale_manager = locale_manager
        self.on_unlocked = on_unlocked

        self.is_locked_down = False
        self.attempting_username = ""

        # UI Controls
        self.lockdown_username = ft.TextField(
            label=self.locale_manager.get_string("security.superuser", "Super Usuário"),
            bgcolor=ft.Colors.WHITE12,
        )
        self.lockdown_password = ft.TextField(
            label=self.locale_manager.get_string("security.password", "Senha"),
            password=True,
            can_reveal_password=True,
            on_submit=self._submit_unlock,
            bgcolor=ft.Colors.WHITE12,
        )
        self.lockdown_error = ft.Text(
            color=ft.Colors.YELLOW_400, visible=False, size=16, weight=ft.FontWeight.BOLD
        )

        self.dialog = ft.AlertDialog(
            modal=True,
            content_padding=0,
            title_padding=0,
            actions_padding=0,
            bgcolor=ft.Colors.RED_900,
            content=ft.Container(
                width=10000,
                height=10000,
                alignment=ft.alignment.center,
                content=ft.Column(
                    [
                        ft.Icon(ft.Icons.GPP_BAD, size=100, color=ft.Colors.WHITE),
                        ft.Text(
                            self.locale_manager.get_string(
                                "security.system_locked_lockdown", "SISTEMA BLOQUEADO (LOCKDOWN)"
                            ),
                            size=40,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.WHITE,
                        ),
                        ft.Text(
                            self.locale_manager.get_string(
                                "security.system_locked_desc2",
                                "Múltiplas tentativas de acesso inválidas. Controle autônomo e conexões de hardware desligadas.",
                            ),
                            size=20,
                            color=ft.Colors.WHITE70,
                        ),
                        ft.Text(
                            self.locale_manager.get_string(
                                "security.system_locked_desc3",
                                "Os semáforos estão operando em seus planos locais seguros.",
                            ),
                            size=16,
                            color=ft.Colors.WHITE70,
                        ),
                        ft.Container(height=40),
                        ft.Container(
                            width=350,
                            content=ft.Column(
                                [
                                    self.lockdown_username,
                                    self.lockdown_password,
                                    self.lockdown_error,
                                    ft.Container(height=10),
                                    ft.ElevatedButton(
                                        self.locale_manager.get_string(
                                            "security.auth_superuser", "AUTENTICAR COMO SUPER USUÁRIO"
                                        ),
                                        on_click=self._submit_unlock,
                                        style=ft.ButtonStyle(
                                            color=ft.Colors.RED_900, bgcolor=ft.Colors.WHITE, padding=20
                                        ),
                                        width=350,
                                    ),
                                ]
                            ),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ),
        )
        self.page.overlay.append(self.dialog)

    def trigger_lockdown(self) -> None:
        self.is_locked_down = True
        self.lockdown_username.value = ""
        self.lockdown_password.value = ""
        self.lockdown_error.visible = False
        self.dialog.open = True
        self.page.update()

    def _submit_unlock(self, e=None) -> None:
        username = self.lockdown_username.value
        password = self.lockdown_password.value
        if not username or not password:
            self.lockdown_error.value = self.locale_manager.get_string(
                "security.err_fill_fields", "Preencha ambos os campos."
            )
            self.lockdown_error.visible = True
            self.page.update()
            return

        self.attempting_username = username
        self.lockdown_error.visible = False
        self.page.update()

        if self.control_client.live_data_provider:
            self.control_client.live_data_provider.send_command_to_backend(
                {"type": "authenticate", "payload": {"username": username, "password": password}}
            )

    def handle_unlock_response(self, success: bool, role: str, message: str) -> None:
        if success:
            if role in ["SUPERUSER", "MASTER"]:
                self.page.session.set("current_user", self.attempting_username)
                self.is_locked_down = False
                self.dialog.open = False
                self.page.update()
                if self.on_unlocked:
                    self.on_unlocked(self.attempting_username)
            else:
                self.lockdown_error.value = self.locale_manager.get_string(
                    "security.err_superuser_only", "Apenas Super Usuários podem desbloquear o sistema."
                )
                self.lockdown_error.visible = True
                self.page.update()
        else:
            self.lockdown_error.value = message or "Credenciais Inválidas"
            self.lockdown_error.visible = True
            self.page.update()
