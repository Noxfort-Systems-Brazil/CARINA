# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Any, Callable, Dict, Optional

import flet as ft

from ui.controllers.database_settings_controller import DatabaseSettingsController
from ui.handlers.locale_manager import LocaleManager


class DatabaseSettingsCard(ft.Card):
    """Card UI for Database Settings (SQLite vs PostgreSQL), delegating testing to DatabaseSettingsController."""

    def __init__(
        self,
        initial_values: Dict[str, Any],
        on_toggle_connection: Optional[Callable[[bool], None]] = None,
        locale_manager: Optional[LocaleManager] = None,
        controller: Optional[DatabaseSettingsController] = None,
    ):
        super().__init__(elevation=2)
        self.initial_values = initial_values
        self.on_toggle_connection = on_toggle_connection
        self.lm = locale_manager
        self.controller = controller or DatabaseSettingsController()
        self.is_connected = str(initial_values.get("db_connected", "False")).lower() == "true"

        # UI Elements
        self.title_text = ft.Text(size=18, weight=ft.FontWeight.BOLD)
        self.subtitle_text = ft.Text(italic=True, size=12, color=ft.Colors.GREY_500)

        self.db_type_dropdown = ft.Dropdown(
            value=str(initial_values.get("db_type", "sqlite")),
            options=[ft.dropdown.Option("sqlite"), ft.dropdown.Option("postgres")],
            on_change=self._on_db_type_change,
            width=300,
            disabled=self.is_connected,
        )

        # PostgreSQL Fields
        self.host_field = ft.TextField(value=str(initial_values.get("db_host", "localhost")), width=200, disabled=self.is_connected)
        self.port_field = ft.TextField(value=str(initial_values.get("db_port", "5432")), width=100, disabled=self.is_connected)
        self.user_field = ft.TextField(value=str(initial_values.get("db_user", "postgres")), width=200, disabled=self.is_connected)
        self.password_field = ft.TextField(value=str(initial_values.get("db_password", "")), password=True, can_reveal_password=True, width=200, disabled=self.is_connected)
        self.dbname_field = ft.TextField(value=str(initial_values.get("db_name", "carina_data")), width=300, disabled=self.is_connected)

        self.postgres_container = ft.Column(
            controls=[
                ft.Row([self.host_field, self.port_field]),
                ft.Row([self.user_field, self.password_field]),
                self.dbname_field,
            ],
            visible=(self.db_type_dropdown.value == "postgres"),
        )

        # Action Buttons
        self.btn_connect = ft.ElevatedButton(icon=ft.Icons.LOGIN_ROUNDED, on_click=self._on_connect_click, visible=not self.is_connected)
        self.btn_disconnect = ft.OutlinedButton(icon=ft.Icons.LOGOUT_ROUNDED, on_click=self._on_disconnect_click, visible=self.is_connected)

        # Status Display
        self.status_icon = ft.Icon(name=ft.Icons.CIRCLE, color=ft.Colors.GREY_500, size=16)
        self.status_text = ft.Text(color=ft.Colors.GREY_500, weight=ft.FontWeight.W_500)
        self.progress_ring = ft.ProgressRing(width=16, height=16, stroke_width=2, visible=False)
        self.status_display = ft.Row([self.progress_ring, self.status_icon, self.status_text], alignment=ft.MainAxisAlignment.START, spacing=5)

        self.content = ft.Container(
            padding=20,
            content=ft.Column(
                controls=[
                    ft.Row([ft.Icon(ft.Icons.STORAGE), self.title_text]),
                    self.subtitle_text,
                    ft.Divider(height=10),
                    self.db_type_dropdown,
                    self.postgres_container,
                    ft.Divider(height=10),
                    ft.Row([ft.Row([self.btn_connect, self.btn_disconnect], spacing=10), self.status_display], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ]
            ),
        )

        if self.lm:
            self.update_translations(self.lm)
        else:
            try:
                self.update_translations(LocaleManager())
            except Exception:
                pass

        if self.is_connected:
            self._set_connected_ui_state()

    def _set_connected_ui_state(self) -> None:
        self.status_icon.name = ft.Icons.CHECK_CIRCLE
        self.status_icon.color = ft.Colors.GREEN_500
        self.status_text.value = self._get_translation("settings_view.db_card.status_connected", "CONECTADO")
        self.status_text.color = ft.Colors.GREEN_500
        self._update_ui_lock_state()

    def _update_ui_lock_state(self) -> None:
        for f in (self.db_type_dropdown, self.host_field, self.port_field, self.user_field, self.password_field, self.dbname_field):
            f.disabled = self.is_connected
        self.btn_connect.visible = not self.is_connected
        self.btn_disconnect.visible = self.is_connected
        if self.page:
            self.update()

    def _on_db_type_change(self, e) -> None:
        self.postgres_container.visible = self.db_type_dropdown.value == "postgres"
        self.status_icon.name = ft.Icons.CIRCLE
        self.status_icon.color = ft.Colors.GREY_500
        self.status_text.value = self._get_translation("settings_view.db_card.status_untested", "NÃO TESTADO")
        self.status_text.color = ft.Colors.GREY_500
        if self.page:
            self.update()

    def _on_connect_click(self, e) -> None:
        self.btn_connect.disabled = True
        self.progress_ring.visible = True
        self.status_icon.visible = False
        self.status_text.value = self._get_translation("settings_view.db_card.status_testing", "TESTANDO...")
        self.status_text.color = ft.Colors.AMBER_500
        if self.page:
            self.update()
        self.controller.test_connection_async(self.get_values(), on_result=self._update_test_result, silent_auto=False)

    def _on_disconnect_click(self, e) -> None:
        self.is_connected = False
        self._update_ui_lock_state()
        self.status_icon.name = ft.Icons.CIRCLE
        self.status_icon.color = ft.Colors.GREY_500
        self.status_text.value = self._get_translation("settings_view.db_card.status_untested", "NÃO TESTADO")
        self.status_text.color = ft.Colors.GREY_500
        if self.on_toggle_connection:
            self.on_toggle_connection(False)
        if self.page:
            self.update()

    def _get_translation(self, key: str, default: str, **kwargs) -> str:
        return self.lm.get_string(key, default=default, **kwargs) if self.lm else default

    def _show_snack_bar(self, message: str, bgcolor: str) -> None:
        if self.page:
            self.page.snack_bar = ft.SnackBar(content=ft.Text(message, color=ft.Colors.WHITE), bgcolor=bgcolor)
            self.page.snack_bar.open = True

    def _update_test_result(self, success: bool, error_msg: str, silent_auto: bool) -> None:
        self.btn_connect.disabled = False
        self.progress_ring.visible = False
        self.status_icon.visible = True

        if success:
            self.is_connected = True
            self.status_icon.name = ft.Icons.CHECK_CIRCLE
            self.status_icon.color = ft.Colors.GREEN_500
            self.status_text.value = self._get_translation("settings_view.db_card.status_connected", "CONECTADO")
            self.status_text.color = ft.Colors.GREEN_500
            self._update_ui_lock_state()

            if not silent_auto:
                msg = self._get_translation("settings_view.db_card.msg_success", "Conexão ao banco de dados estabelecida com sucesso!")
                self._show_snack_bar(msg, ft.Colors.GREEN_700)
                if self.on_toggle_connection:
                    self.on_toggle_connection(True)
        else:
            if not silent_auto:
                self.is_connected = False
                self._update_ui_lock_state()
                err_label = self._get_translation("settings_view.db_card.msg_error", f"Erro: {error_msg}", error=error_msg)
                self._show_snack_bar(err_label, ft.Colors.RED_700)
            self.status_icon.name = ft.Icons.ERROR
            self.status_icon.color = ft.Colors.RED_500
            self.status_text.value = self._get_translation("settings_view.db_card.status_error", "ERRO DE CONEXÃO")
            self.status_text.color = ft.Colors.RED_500

        if self.page:
            self.update()

    def get_values(self) -> Dict[str, Any]:
        return {
            "db_type": self.db_type_dropdown.value,
            "db_host": self.host_field.value,
            "db_port": self.port_field.value,
            "db_user": self.user_field.value,
            "db_password": self.password_field.value,
            "db_name": self.dbname_field.value,
            "db_connected": str(self.is_connected),
        }

    def set_values(self, values: Dict[str, Any]) -> None:
        self.db_type_dropdown.value = str(values.get("db_type", "sqlite"))
        self.host_field.value = str(values.get("db_host", "localhost"))
        self.port_field.value = str(values.get("db_port", "5432"))
        self.user_field.value = str(values.get("db_user", "postgres"))
        self.password_field.value = str(values.get("db_password", ""))
        self.dbname_field.value = str(values.get("db_name", "carina_data"))

        is_conn = str(values.get("db_connected", "False")).lower() == "true"
        if is_conn != self.is_connected:
            self.is_connected = is_conn
            if self.is_connected:
                self._set_connected_ui_state()
            else:
                self._update_ui_lock_state()
                self.status_icon.name = ft.Icons.CIRCLE
                self.status_icon.color = ft.Colors.GREY_500
                self.status_text.value = self._get_translation("settings_view.db_card.status_untested", "NÃO TESTADO")
                self.status_text.color = ft.Colors.GREY_500

        self.postgres_container.visible = self.db_type_dropdown.value == "postgres"
        if self.page:
            self.update()

    def update_translations(self, lm: LocaleManager) -> None:
        self.lm = lm
        self.title_text.value = lm.get_string("settings_view.db_card.title", default="Configurações de Banco de Dados")
        self.subtitle_text.value = lm.get_string("settings_view.db_card.subtitle", default="O PostgreSQL é recomendado para alta carga e Machine Learning distribuído.")
        self.db_type_dropdown.label = lm.get_string("settings_view.db_card.type_label", default="Tipo de Banco de Dados")

        if len(self.db_type_dropdown.options) >= 2:
            self.db_type_dropdown.options[0].text = lm.get_string("settings_view.db_card.option_sqlite", default="SQLite (Local)")
            self.db_type_dropdown.options[1].text = lm.get_string("settings_view.db_card.option_postgres", default="PostgreSQL (Remoto/Avançado)")

        self.host_field.label = lm.get_string("settings_view.db_card.host", default="Host")
        self.port_field.label = lm.get_string("settings_view.db_card.port", default="Porta")
        self.user_field.label = lm.get_string("settings_view.db_card.user", default="Usuário")
        self.password_field.label = lm.get_string("settings_view.db_card.password", default="Senha")
        self.dbname_field.label = lm.get_string("settings_view.db_card.dbname", default="Nome do Banco")
        self.btn_connect.text = lm.get_string("settings_view.db_card.btn_connect", default="Conectar")
        self.btn_disconnect.text = lm.get_string("settings_view.db_card.btn_disconnect", default="Desconectar")

        if self.status_icon.name == ft.Icons.CIRCLE:
            self.status_text.value = lm.get_string("settings_view.db_card.status_untested", default="NÃO TESTADO")
        elif self.status_icon.name == ft.Icons.CHECK_CIRCLE:
            self.status_text.value = lm.get_string("settings_view.db_card.status_connected", default="CONECTADO")
        elif self.status_icon.name == ft.Icons.ERROR:
            self.status_text.value = lm.get_string("settings_view.db_card.status_error", default="ERRO DE CONEXÃO")

        if self.page:
            self.update()
