# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Any, Callable, Dict, Optional
import flet as ft

from ui.handlers.locale_manager import LocaleManager


class YellowScheduleSectionWidget(ft.Container):
    """
    Component for presenting yellow schedule actions and badge in specific controls.
    Satisfies Single Responsibility Principle (SRP) by extracting schedule controls UI.
    """

    def __init__(
        self,
        locale_manager: LocaleManager,
        on_quick_enable: Optional[Callable[[Any], None]] = None,
        on_toggle_schedule: Optional[Callable[[Any], None]] = None,
        on_edit_schedule: Optional[Callable[[Any], None]] = None,
    ):
        super().__init__(
            padding=8,
            border=ft.border.all(1, ft.Colors.BLUE_GREY_700),
            border_radius=8,
            bgcolor=ft.Colors.with_opacity(0.2, ft.Colors.BLACK),
        )
        self.locale_manager = locale_manager
        self.on_quick_enable = on_quick_enable
        self.on_toggle_schedule = on_toggle_schedule
        self.on_edit_schedule = on_edit_schedule

        self.schedule_icon = ft.Icon(ft.Icons.SCHEDULE_ROUNDED, size=18, color=ft.Colors.WHITE54)
        self.schedule_title = ft.Text("Amarelo Intermitente:", size=12, weight=ft.FontWeight.BOLD)
        self.switch_quick_enable = ft.Switch(value=False, on_change=self.on_quick_enable)
        self.schedule_badge_text = ft.Text(size=11, weight=ft.FontWeight.W_600)
        self.schedule_badge = ft.Container(
            content=self.schedule_badge_text,
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
            border_radius=6,
            bgcolor=ft.Colors.BLUE_GREY_800,
        )
        self.btn_toggle_schedule = ft.OutlinedButton(
            icon=ft.Icons.NIGHTLIGHT_ROUNDED,
            text="Agendamento Noturno",
            width=230,
            on_click=self.on_toggle_schedule,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)),
        )
        self.btn_edit_schedule = ft.OutlinedButton(
            icon=ft.Icons.TUNE_ROUNDED,
            text="Personalizar Horário",
            width=230,
            on_click=self.on_edit_schedule,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)),
        )

        self.content = ft.Column(
            [
                ft.Row(
                    [
                        self.schedule_icon,
                        self.schedule_title,
                        ft.Container(expand=True),
                        self.switch_quick_enable,
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                self.schedule_badge,
                self.btn_toggle_schedule,
                self.btn_edit_schedule,
            ],
            spacing=6,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def update_translations(self, lm: LocaleManager):
        self.locale_manager = lm
        self.schedule_title.value = lm.get_string(
            "dashboard_view.yellow_schedule_title", default="Amarelo Intermitente:"
        )
        self.btn_edit_schedule.text = lm.get_string(
            "dashboard_view.yellow_schedule_edit_btn", default="Personalizar Horário"
        )
        self.switch_quick_enable.tooltip = lm.get_string(
            "dashboard_view.yellow_schedule_dialog_enable", default="Ativar Agendamento Noturno"
        )

    def update_display(self, status: Dict[str, Any]):
        enabled = status.get("enabled", False)
        start = status.get("start", "23:00")
        end = status.get("end", "05:00")
        is_all = status.get("is_all", False)
        is_sched = status.get("is_scheduled", False)
        is_active = status.get("is_active_now", False)

        self.switch_quick_enable.value = bool(enabled)
        lm = self.locale_manager

        if not enabled:
            self.schedule_icon.color = ft.Colors.GREY_600
            self.schedule_badge.bgcolor = ft.Colors.GREY_800
            self.schedule_badge_text.color = ft.Colors.WHITE54
            if is_all:
                all_msg = lm.get_string("dashboard_view.yellow_schedule_all_active", default="Ativo para toda a malha")
                self.schedule_badge_text.value = f"DESATIVADO ({all_msg}: {start} - {end})"
                self.btn_toggle_schedule.visible = False
            elif is_sched:
                tmpl = lm.get_string(
                    "dashboard_view.yellow_schedule_inactive_included",
                    default="DESATIVADO (Na lista: {start} - {end})",
                )
                self.schedule_badge_text.value = tmpl.format(start=start, end=end)
                self.btn_toggle_schedule.visible = True
                self.btn_toggle_schedule.text = lm.get_string(
                    "dashboard_view.yellow_schedule_toggle_remove", default="Remover do Horário Noturno"
                )
                self.btn_toggle_schedule.icon = ft.Icons.ALARM_OFF_ROUNDED
            else:
                tmpl = lm.get_string(
                    "dashboard_view.yellow_schedule_inactive_window", default="DESATIVADO ({start} - {end})"
                )
                self.schedule_badge_text.value = tmpl.format(start=start, end=end)
                self.btn_toggle_schedule.visible = True
                self.btn_toggle_schedule.text = lm.get_string(
                    "dashboard_view.yellow_schedule_toggle_add", default="Incluir no Horário Noturno"
                )
                self.btn_toggle_schedule.icon = ft.Icons.ADD_ALARM_ROUNDED
        elif is_all or is_sched:
            self.schedule_icon.color = ft.Colors.AMBER_400 if is_active else ft.Colors.CYAN_300
            if is_active:
                tmpl = lm.get_string("dashboard_view.yellow_schedule_active", default="ATIVO AGORA ({start} - {end})")
                self.schedule_badge_text.value = tmpl.format(start=start, end=end)
                self.schedule_badge.bgcolor = ft.Colors.AMBER_900
                self.schedule_badge_text.color = ft.Colors.AMBER_200
            else:
                tmpl = lm.get_string("dashboard_view.yellow_schedule_pending", default="PROGRAMADO ({start} - {end})")
                self.schedule_badge_text.value = tmpl.format(start=start, end=end)
                self.schedule_badge.bgcolor = ft.Colors.CYAN_900
                self.schedule_badge_text.color = ft.Colors.CYAN_200

            self.btn_toggle_schedule.visible = not is_all
            if not is_all:
                self.btn_toggle_schedule.text = lm.get_string(
                    "dashboard_view.yellow_schedule_toggle_remove", default="Remover do Horário Noturno"
                )
                self.btn_toggle_schedule.icon = ft.Icons.ALARM_OFF_ROUNDED
        else:
            self.schedule_icon.color = ft.Colors.GREY_600
            self.schedule_badge_text.value = lm.get_string(
                "dashboard_view.yellow_schedule_disabled", default="NÃO PROGRAMADO"
            )
            self.schedule_badge.bgcolor = ft.Colors.GREY_800
            self.schedule_badge_text.color = ft.Colors.WHITE54
            self.btn_toggle_schedule.visible = True
            self.btn_toggle_schedule.text = lm.get_string(
                "dashboard_view.yellow_schedule_toggle_add", default="Incluir no Horário Noturno"
            )
            self.btn_toggle_schedule.icon = ft.Icons.ADD_ALARM_ROUNDED
