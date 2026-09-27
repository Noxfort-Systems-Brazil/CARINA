# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: ui/cards/database_settings_card.py
# Author: Gabriel Moraes
# Date: September 2026

from typing import Any, Callable, Dict, Optional

import flet as ft

from ui.cards.database_connection_tester import DatabaseConnectionTester
from ui.handlers.locale_manager import LocaleManager


class DatabaseSettingsCard(ft.Card):
    """Card UI for Database Settings (SQLite vs PostgreSQL), delegating connection testing."""

    def __init__(self, initial_values: Dict[str, Any], on_toggle_connection: Optional[Callable[[bool], None]] = None):
        super().__init__(elevation=2)
        self.initial_values = initial_values
        self.on_toggle_connection = on_toggle_connection
        self.lm = None
        self.is_connected = str(initial_values.get("db_connected", "False")).lower() == "true"

        # UI Elements
        self.title_text = ft.Text("Configurações de Banco de Dados", size=18, weight=ft.FontWeight.BOLD)
        self.subtitle_text = ft.Text(
            "O PostgreSQL é recomendado para alta carga e Machine Learning distribuído.",
            italic=True,
            size=12,
            color=ft.Colors.GREY_500,
        )

        self.db_type_dropdown = ft.Dropdown(
            label="Tipo de Banco de Dados",
            value=str(initial_values.get("db_type", "sqlite")),
            options=[
                ft.dropdown.Option("sqlite", "SQLite (Local)"),
                ft.dropdown.Option("postgres", "PostgreSQL (Remoto/Avançado)"),
            ],
            on_change=self._on_db_type_change,
            width=300,
            disabled=self.is_connected,
        )

        # PostgreSQL Fields
        self.host_field = ft.TextField(
            label="Host", value=str(initial_values.get("db_host", "localhost")), width=200, disabled=self.is_connected
        )
        self.port_field = ft.TextField(
            label="Porta", value=str(initial_values.get("db_port", "5432")), width=100, disabled=self.is_connected
        )
        self.user_field = ft.TextField(
            label="Usuário", value=str(initial_values.get("db_user", "postgres")), width=200, disabled=self.is_connected
        )
        self.password_field = ft.TextField(
            label="Senha",
            value=str(initial_values.get("db_password", "")),
            password=True,
            can_reveal_password=True,
            width=200,
            disabled=self.is_connected,
        )
        self.dbname_field = ft.TextField(
            label="Nome do Banco (DB Name)",
            value=str(initial_values.get("db_name", "carina_data")),
            width=300,
            disabled=self.is_connected,
        )

        self.postgres_container = ft.Column(
            controls=[
                ft.Row([self.host_field, self.port_field]),
                ft.Row([self.user_field, self.password_field]),
                self.dbname_field,
            ],
            visible=(self.db_type_dropdown.value == "postgres"),
        )

        # Action Buttons
        self.btn_connect = ft.ElevatedButton(
            text="Conectar / Testar",
            icon=ft.Icons.LOGIN_ROUNDED,
            on_click=self._on_connect_click,
            visible=not self.is_connected,
        )
        self.btn_disconnect = ft.OutlinedButton(
            text="Desconectar",
            icon=ft.Icons.LOGOUT_ROUNDED,
            on_click=self._on_disconnect_click,
            visible=self.is_connected,
        )

        # Status Display
        self.status_icon = ft.Icon(name=ft.Icons.CIRCLE, color=ft.Colors.GREY_500, size=16)
        self.status_text = ft.Text("NÃO TESTADO", color=ft.Colors.GREY_500, weight=ft.FontWeight.W_500)
        self.progress_ring = ft.ProgressRing(width=16, height=16, stroke_width=2, visible=False)
        self.status_display = ft.Row(
            [self.progress_ring, self.status_icon, self.status_text], alignment=ft.MainAxisAlignment.START, spacing=5
        )

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
                    ft.Row(
                        [ft.Row([self.btn_connect, self.btn_disconnect], spacing=10), self.status_display],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                ]
            ),
        )

        if self.is_connected:
            self._trigger_silent_auto_test()

    def _trigger_silent_auto_test(self) -> None:
        """Silently auto-tests the connection if initialized as connected."""
        self.status_icon.name = ft.Icons.CHECK_CIRCLE
        self.status_icon.color = ft.Colors.GREEN_500
        self.status_text.value = "CONECTADO"
        self.status_text.color = ft.Colors.GREEN_500

        DatabaseConnectionTester.test_connection_async(
            db_type=self.db_type_dropdown.value,
            host=self.host_field.value,
            port=self.port_field.value,
            user=self.user_field.value,
            password=self.password_field.value,
            dbname=self.dbname_field.value,
            callback=lambda success, err: self._update_test_result(success, err, silent_auto=True),
        )

    def _update_ui_lock_state(self) -> None:
        for f in (
            self.db_type_dropdown,
            self.host_field,
            self.port_field,
            self.user_field,
            self.password_field,
            self.dbname_field,
        ):
            f.disabled = self.is_connected
        self.btn_connect.visible = not self.is_connected
        self.btn_disconnect.visible = self.is_connected
        if self.page:
            self.update()

    def _on_db_type_change(self, e) -> None:
        self.postgres_container.visible = self.db_type_dropdown.value == "postgres"
        self.status_icon.name = ft.Icons.CIRCLE
        self.status_icon.color = ft.Colors.GREY_500
        status_untested = (
            self.lm.get_string("settings_view.db_card.status_untested", default="NÃO TESTADO")
            if self.lm
            else "NÃO TESTADO"
        )
        self.status_text.value = status_untested
        self.status_text.color = ft.Colors.GREY_500
        if self.page:
            self.update()

    def _on_connect_click(self, e) -> None:
        self.btn_connect.disabled = True
        self.progress_ring.visible = True
        self.status_icon.visible = False
        status_testing = (
            self.lm.get_string("settings_view.db_card.status_testing", default="TESTANDO...")
            if self.lm
            else "TESTANDO..."
        )
        self.status_text.value = status_testing
        self.status_text.color = ft.Colors.AMBER_500
        if self.page:
            self.update()

        DatabaseConnectionTester.test_connection_async(
            db_type=self.db_type_dropdown.value,
            host=self.host_field.value,
            port=self.port_field.value,
            user=self.user_field.value,
            password=self.password_field.value,
            dbname=self.dbname_field.value,
            callback=lambda success, err: self._update_test_result(success, err, silent_auto=False),
        )

    def _on_disconnect_click(self, e) -> None:
        self.is_connected = False
        self._update_ui_lock_state()
        self.status_icon.name = ft.Icons.CIRCLE
        self.status_icon.color = ft.Colors.GREY_500
        self.status_text.value = (
            self.lm.get_string("settings_view.db_card.status_untested", default="NÃO TESTADO")
            if self.lm
            else "NÃO TESTADO"
        )
        self.status_text.color = ft.Colors.GREY_500
        if self.on_toggle_connection:
            self.on_toggle_connection(False)
        if self.page:
            self.update()

    def _update_test_result(self, success: bool, error_msg: str, silent_auto: bool) -> None:
        self.btn_connect.disabled = False
        self.progress_ring.visible = False
        self.status_icon.visible = True

        if success:
            self.is_connected = True
            self.status_icon.name = ft.Icons.CHECK_CIRCLE
            self.status_icon.color = ft.Colors.GREEN_500
            self.status_text.value = (
                self.lm.get_string("settings_view.db_card.status_connected", default="CONECTADO")
                if self.lm
                else "CONECTADO"
            )
            self.status_text.color = ft.Colors.GREEN_500
            self._update_ui_lock_state()

            if not silent_auto:
                msg = (
                    self.lm.get_string(
                        "settings_view.db_card.msg_success",
                        default="Conexão ao banco de dados estabelecida com sucesso!",
                    )
                    if self.lm
                    else "Conexão ao banco de dados estabelecida com sucesso!"
                )
                if self.page:
                    self.page.snack_bar = ft.SnackBar(
                        content=ft.Text(msg, color=ft.colors.WHITE), bgcolor=ft.colors.GREEN_700
                    )
                    self.page.snack_bar.open = True
                if self.on_toggle_connection:
                    self.on_toggle_connection(True)
        else:
            self.is_connected = False
            self.status_icon.name = ft.Icons.ERROR
            self.status_icon.color = ft.Colors.RED_500
            self.status_text.value = (
                self.lm.get_string("settings_view.db_card.status_error", default="ERRO DE CONEXÃO")
                if self.lm
                else "ERRO DE CONEXÃO"
            )
            self.status_text.color = ft.Colors.RED_500
            self._update_ui_lock_state()

            if self.page:
                err_label = (
                    self.lm.get_string("settings_view.db_card.msg_error", default="Erro: {error}", error=error_msg)
                    if self.lm
                    else f"Erro: {error_msg}"
                )
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text(err_label, color=ft.colors.WHITE), bgcolor=ft.colors.RED_700
                )
                self.page.snack_bar.open = True

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
            self._update_ui_lock_state()
            if self.is_connected:
                self._trigger_silent_auto_test()

        self.postgres_container.visible = self.db_type_dropdown.value == "postgres"
        if self.page:
            self.update()

    def update_translations(self, lm: LocaleManager) -> None:
        self.lm = lm
        self.title_text.value = lm.get_string("settings_view.db_card.title", default="Configurações de Banco de Dados")
        self.subtitle_text.value = lm.get_string(
            "settings_view.db_card.subtitle",
            default="O PostgreSQL é recomendado para alta carga e Machine Learning distribuído.",
        )
        self.db_type_dropdown.label = lm.get_string(
            "settings_view.db_card.type_label", default="Tipo de Banco de Dados"
        )

        if len(self.db_type_dropdown.options) >= 2:
            self.db_type_dropdown.options[0].text = lm.get_string(
                "settings_view.db_card.option_sqlite", default="SQLite (Local)"
            )
            self.db_type_dropdown.options[1].text = lm.get_string(
                "settings_view.db_card.option_postgres", default="PostgreSQL (Remoto/Avançado)"
            )

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
