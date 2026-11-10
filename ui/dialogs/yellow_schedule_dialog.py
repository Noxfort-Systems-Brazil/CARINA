# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Callable, Optional

import flet as ft

from ui.handlers.locale_manager import LocaleManager


class YellowScheduleDialog:
    """Manages the modal dialog for configuring intermittent yellow night schedules."""

    def __init__(
        self,
        locale_manager: LocaleManager,
        on_save: Optional[Callable[[str, str, bool, bool], None]] = None,
    ):
        self.locale_manager = locale_manager
        self.on_save = on_save
        self.page: Optional[ft.Page] = None

        self.schedule_dialog: Optional[ft.AlertDialog] = None
        self.dlg_title_text: Optional[ft.Text] = None
        self.dlg_switch_enabled: Optional[ft.Switch] = None
        self.dlg_tf_start: Optional[ft.TextField] = None
        self.dlg_tf_end: Optional[ft.TextField] = None
        self.dlg_switch_all: Optional[ft.Switch] = None
        self.dlg_error_text: Optional[ft.Text] = None
        self.dlg_btn_save: Optional[ft.ElevatedButton] = None
        self.dlg_btn_cancel: Optional[ft.TextButton] = None

    @staticmethod
    def is_valid_time_str(val: str) -> bool:
        if not val or ":" not in val:
            return False
        parts = val.split(":")
        if len(parts) != 2:
            return False
        try:
            h = int(parts[0])
            m = int(parts[1])
            return 0 <= h <= 23 and 0 <= m <= 59
        except ValueError:
            return False

    def mount(self, page: ft.Page) -> None:
        self.page = page
        if not self.page or self.schedule_dialog:
            return

        lm = self.locale_manager
        self.dlg_title_text = ft.Text(
            lm.get_string("dashboard_view.yellow_schedule_dialog_title", default="Personalizar Agendamento Noturno"),
            size=16,
            weight=ft.FontWeight.BOLD,
        )
        self.dlg_switch_enabled = ft.Switch(
            label=lm.get_string("dashboard_view.yellow_schedule_dialog_enable", default="Ativar Agendamento Noturno"),
            value=False,
        )
        self.dlg_tf_start = ft.TextField(
            label=lm.get_string("dashboard_view.yellow_schedule_dialog_start", default="Horário Início (HH:MM)"),
            value="23:00",
            width=135,
            max_length=5,
            hint_text="23:00",
        )
        self.dlg_tf_end = ft.TextField(
            label=lm.get_string("dashboard_view.yellow_schedule_dialog_end", default="Horário Término (HH:MM)"),
            value="05:00",
            width=135,
            max_length=5,
            hint_text="05:00",
        )
        self.dlg_switch_all = ft.Switch(
            label=lm.get_string("dashboard_view.yellow_schedule_dialog_all", default="Aplicar a todos os semáforos da malha"),
            value=False,
        )
        self.dlg_error_text = ft.Text(color=ft.Colors.RED_400, size=11, visible=False)
        self.dlg_btn_cancel = ft.TextButton(
            lm.get_string("dashboard_view.yellow_schedule_dialog_cancel", default="Cancelar"),
            on_click=self.close,
        )
        self.dlg_btn_save = ft.ElevatedButton(
            lm.get_string("dashboard_view.yellow_schedule_dialog_save", default="Salvar Horário"),
            icon=ft.Icons.SAVE_ROUNDED,
            on_click=self._handle_save_click,
        )

        self.schedule_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([ft.Icon(ft.Icons.TUNE_ROUNDED, color=ft.Colors.AMBER_400), self.dlg_title_text]),
            content=ft.Column(
                [
                    self.dlg_switch_enabled,
                    ft.Row([self.dlg_tf_start, self.dlg_tf_end], spacing=10),
                    self.dlg_switch_all,
                    self.dlg_error_text,
                ],
                tight=True,
                spacing=12,
            ),
            actions=[self.dlg_btn_cancel, self.dlg_btn_save],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        if self.schedule_dialog not in self.page.overlay:
            self.page.overlay.append(self.schedule_dialog)

    def open(self, cfg: dict) -> None:
        if not self.schedule_dialog and self.page:
            self.mount(self.page)
        if not self.schedule_dialog:
            return

        self.dlg_switch_enabled.value = bool(cfg.get("yellow_schedule_enabled", False))
        self.dlg_tf_start.value = str(cfg.get("yellow_schedule_start", "23:00"))
        self.dlg_tf_end.value = str(cfg.get("yellow_schedule_end", "05:00"))
        self.dlg_switch_all.value = bool(cfg.get("yellow_schedule_all_semaphores", False))
        self.dlg_error_text.visible = False
        self.schedule_dialog.open = True
        if self.page:
            self.page.update()

    def close(self, e=None) -> None:
        if self.schedule_dialog:
            self.schedule_dialog.open = False
            if self.page:
                self.page.update()

    def _handle_save_click(self, e) -> None:
        start_val = (self.dlg_tf_start.value or "").strip()
        end_val = (self.dlg_tf_end.value or "").strip()

        if not self.is_valid_time_str(start_val) or not self.is_valid_time_str(end_val):
            err_msg = self.locale_manager.get_string(
                "dashboard_view.yellow_schedule_dialog_err_format",
                default="Formato de hora inválido (HH:MM)",
            )
            self.dlg_error_text.value = err_msg
            self.dlg_error_text.visible = True
            if self.page:
                self.page.update()
            return

        self.dlg_error_text.visible = False
        enabled_val = bool(self.dlg_switch_enabled.value)
        all_val = bool(self.dlg_switch_all.value)

        if self.on_save:
            self.on_save(start_val, end_val, all_val, enabled_val)

        self.close()
