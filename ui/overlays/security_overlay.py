# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Callable, Optional

import flet as ft

from ui.overlays.lockdown_dialog import LockdownDialog


class SecurityUI:
    """Manages the Security Authentication Dialog and coordinates the Global Lockdown Overlay."""

    def __init__(self, page: ft.Page, control_client, locale_manager):
        self.page = page
        self.control_client = control_client
        self.locale_manager = locale_manager

        self.pending_action: Optional[Callable] = None
        self.attempting_username: str = ""

        # --- Auth Dialog Components ---
        self.username_field = ft.TextField(
            label=self.locale_manager.get_string("security.username", "Nome de Usuário"), autofocus=True
        )
        self.password_field = ft.TextField(
            label=self.locale_manager.get_string("security.password", "Senha"),
            password=True,
            can_reveal_password=True,
            on_submit=self._submit_auth,
        )
        self.auth_error_text = ft.Text(color=ft.Colors.RED_400, visible=False)
        self.auth_progress = ft.ProgressBar(visible=False)

        self.auth_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.SECURITY),
                    ft.Text(self.locale_manager.get_string("security.auth_required", "Autenticação Necessária")),
                ]
            ),
            content=ft.Column(
                [self.username_field, self.password_field, self.auth_error_text, self.auth_progress], tight=True
            ),
            actions=[
                ft.TextButton(
                    self.locale_manager.get_string("security.cancel", "Cancelar"), on_click=self._cancel_auth
                ),
                ft.ElevatedButton(
                    self.locale_manager.get_string("security.authenticate", "Autenticar"), on_click=self._submit_auth
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.overlay.append(self.auth_dialog)

        # Dedicated Lockdown Overlay Component
        self.lockdown = LockdownDialog(
            page=self.page,
            control_client=self.control_client,
            locale_manager=self.locale_manager,
        )

    @property
    def is_locked_down(self) -> bool:
        return self.lockdown.is_locked_down

    @is_locked_down.setter
    def is_locked_down(self, val: bool):
        self.lockdown.is_locked_down = val

    @property
    def lockdown_dialog(self) -> ft.AlertDialog:
        return self.lockdown.dialog

    def request_auth(self, on_success: Callable):
        """Opens the auth dialog and stores the callback."""
        if self.is_locked_down:
            return

        self.pending_action = on_success
        self.username_field.value = ""
        self.password_field.value = ""
        self.auth_error_text.visible = False
        self.auth_progress.visible = False
        self.auth_dialog.open = True
        self.page.update()

    def _cancel_auth(self, e):
        self.pending_action = None
        self.auth_dialog.open = False
        self.page.update()

    def _submit_auth(self, e):
        username = self.username_field.value
        password = self.password_field.value
        if not username or not password:
            self.auth_error_text.value = self.locale_manager.get_string(
                "security.err_fill_fields", "Preencha ambos os campos."
            )
            self.auth_error_text.visible = True
            self.page.update()
            return

        self.attempting_username = username
        self.auth_error_text.visible = False
        self.auth_progress.visible = True
        self.username_field.disabled = True
        self.password_field.disabled = True
        self.page.update()

        if self.control_client.live_data_provider:
            self.control_client.live_data_provider.send_command_to_backend(
                {"type": "authenticate", "payload": {"username": username, "password": password}}
            )

    def trigger_lockdown(self):
        """Called when backend informs a lockdown event."""
        self.auth_dialog.open = False
        self.pending_action = None
        self.lockdown.trigger_lockdown()

    def handle_auth_response(self, payload: dict):
        """Called by the main loop when backend responds."""
        success = payload.get("success", False)

        if self.is_locked_down:
            role = payload.get("role", "")
            message = payload.get("message", "Credenciais Inválidas")
            self.lockdown.handle_unlock_response(success, role, message)
        else:
            if success:
                self.page.session.set("current_user", self.attempting_username)
                self.auth_dialog.open = False
                self.username_field.disabled = False
                self.password_field.disabled = False
                self.page.update()

                if self.pending_action:
                    self.pending_action()
                    self.pending_action = None
            else:
                self.auth_progress.visible = False
                self.username_field.disabled = False
                self.password_field.disabled = False
                self.auth_error_text.value = payload.get("message", "Credenciais Inválidas")
                self.auth_error_text.visible = True
                self.page.update()
