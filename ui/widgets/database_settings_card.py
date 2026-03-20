# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: ui/widgets/database_settings_card.py
# Author: Gabriel Moraes
# Date: 2026-03-04

import flet as ft
from typing import Dict, Any, Callable
from ui.handlers.locale_manager import LocaleManager

class DatabaseSettingsCard(ft.Card):
    """
    Card UI para configurações de Banco de Dados.
    Permite alternar entre SQLite e PostgreSQL, revelando campos extras para o Postgres.
    """
    def __init__(self, initial_values: Dict[str, Any]):
        super().__init__(elevation=2)
        self.initial_values = initial_values
        
        # Elementos de UI
        self.db_type_dropdown = ft.Dropdown(
            label="Tipo de Banco de Dados",
            value=str(initial_values.get('db_type', 'sqlite')),
            options=[
                ft.dropdown.Option("sqlite", "SQLite (Local)"),
                ft.dropdown.Option("postgres", "PostgreSQL (Remoto/Avançado)")
            ],
            on_change=self._on_db_type_change,
            width=300
        )

        # Campos PostgreSQL (ocultos se sqlite)
        self.host_field = ft.TextField(label="Host", value=str(initial_values.get('db_host', 'localhost')), width=200)
        self.port_field = ft.TextField(label="Porta", value=str(initial_values.get('db_port', '5432')), width=100)
        self.user_field = ft.TextField(label="Usuário", value=str(initial_values.get('db_user', 'postgres')), width=200)
        self.password_field = ft.TextField(label="Senha", value=str(initial_values.get('db_password', '')), password=True, can_reveal_password=True, width=200)
        self.dbname_field = ft.TextField(label="Nome do Banco (DB Name)", value=str(initial_values.get('db_name', 'carina_data')), width=300)

        self.postgres_container = ft.Column(
            controls=[
                ft.Row([self.host_field, self.port_field]),
                ft.Row([self.user_field, self.password_field]),
                self.dbname_field
            ],
            visible=(self.db_type_dropdown.value == "postgres")
        )

        self.content = ft.Container(
            padding=20,
            content=ft.Column(
                controls=[
                    ft.Text("Configurações de Banco de Dados", size=18, weight=ft.FontWeight.BOLD),
                    ft.Text("O PostgreSQL é recomendado para alta carga e Machine Learning distribuído. Requer reiniciar o backend.", italic=True, size=12, color=ft.Colors.GREY_500),
                    self.db_type_dropdown,
                    self.postgres_container
                ]
            )
        )

    def _on_db_type_change(self, e):
        self.postgres_container.visible = (self.db_type_dropdown.value == "postgres")
        self.update()

    def get_settings(self) -> Dict[str, Any]:
        """Obtém os valores preenchidos no Card"""
        return {
            'db_type': self.db_type_dropdown.value,
            'db_host': self.host_field.value,
            'db_port': self.port_field.value,
            'db_user': self.user_field.value,
            'db_password': self.password_field.value,
            'db_name': self.dbname_field.value
        }
