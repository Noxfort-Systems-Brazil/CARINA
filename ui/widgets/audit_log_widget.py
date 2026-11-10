# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import logging
import os
from datetime import datetime

import flet as ft

from src.utils.paths import get_base_output_dir
from ui.handlers.locale_manager import LocaleManager


class AuditLogWidget(ft.Container):
    def __init__(self, locale_manager: LocaleManager):
        super().__init__(expand=True)
        self.locale_manager = locale_manager
        self.audit_file = os.path.join(get_base_output_dir(), "results", "audit_log.json")

        self.title = ft.Text(
            self.locale_manager.get_string("audit.title", "Registro de Auditoria (Audit Logs)"),
            size=20,
            weight=ft.FontWeight.BOLD,
        )

        self.col_date_text = ft.Text(self.locale_manager.get_string("audit.date_time", "Data/Hora"))
        self.col_user_text = ft.Text(self.locale_manager.get_string("audit.user", "Usuário"))
        self.col_action_text = ft.Text(self.locale_manager.get_string("audit.action", "Ação"))
        self.col_details_text = ft.Text(self.locale_manager.get_string("audit.details", "Detalhes"))

        self.table = ft.DataTable(
            columns=[
                ft.DataColumn(self.col_date_text),
                ft.DataColumn(self.col_user_text),
                ft.DataColumn(self.col_action_text),
                ft.DataColumn(self.col_details_text),
            ],
            rows=[],
            heading_row_color=ft.Colors.BLACK26,
            data_row_min_height=40,
            data_row_max_height=80,
            column_spacing=20,
            show_bottom_border=True,
        )

        self.list_view = ft.ListView(expand=True, controls=[self.table])

        self.refresh_btn = ft.ElevatedButton(
            self.locale_manager.get_string("audit.refresh", "Atualizar"),
            icon=ft.Icons.REFRESH,
            on_click=self._load_logs,
        )

        self.content = ft.Column(
            [
                ft.Row(
                    [ft.Icon(ft.Icons.POLICY), self.title, self.refresh_btn],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Divider(),
                ft.Container(
                    content=self.list_view, expand=True, border=ft.border.all(1, ft.Colors.WHITE24), border_radius=5
                ),
            ]
        )

    def did_mount(self):
        self._load_logs()

    def _load_logs(self, e=None):
        if not os.path.exists(self.audit_file):
            self.table.rows.clear()
            if self.page:
                self.update()
            return

        try:
            with open(self.audit_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Show newest records first
            data = list(reversed(data))

            rows = []
            for entry in data:
                try:
                    dt = datetime.fromisoformat(entry.get("timestamp", ""))
                    time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    time_str = entry.get("timestamp", "")

                rows.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(time_str, size=12)),
                            ft.DataCell(ft.Text(entry.get("username", "Unknown"), size=12, weight=ft.FontWeight.BOLD)),
                            ft.DataCell(ft.Text(entry.get("action", ""), size=12, color=ft.Colors.AMBER_400)),
                            ft.DataCell(ft.Text(entry.get("details", ""), size=12, italic=True)),
                        ]
                    )
                )

            self.table.rows = rows
            if self.page:
                self.update()

        except Exception as ex:
            logging.error(f"[AuditLogWidget] Erro ao carregar logs: {ex}", exc_info=True)

    def update_translations(self, lm: LocaleManager):
        self.locale_manager = lm
        self.title.value = self.locale_manager.get_string("audit.title", "Registro de Auditoria (Audit Logs)")
        self.refresh_btn.text = self.locale_manager.get_string("audit.refresh", "Atualizar")
        self.col_date_text.value = self.locale_manager.get_string("audit.date_time", "Data/Hora")
        self.col_user_text.value = self.locale_manager.get_string("audit.user", "Usuário")
        self.col_action_text.value = self.locale_manager.get_string("audit.action", "Ação")
        self.col_details_text.value = self.locale_manager.get_string("audit.details", "Detalhes")
        if self.page:
            self.update()
