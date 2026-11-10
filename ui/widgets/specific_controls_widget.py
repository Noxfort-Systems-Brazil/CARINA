# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Callable, Dict

import flet as ft

from ui.clients.control_client import ControlClient
from ui.components.semaphore_actions import SemaphoreActionsWidget
from ui.components.semaphore_info_display import SemaphoreInfoDisplayWidget
from ui.components.yellow_schedule_section import YellowScheduleSectionWidget
from ui.dialogs.confirmation_dialog_manager import ConfirmationDialogManager
from ui.dialogs.yellow_schedule_dialog import YellowScheduleDialog
from ui.handlers.locale_manager import LocaleManager
from ui.handlers.specific_controls_handler import SpecificControlsHandler


class SpecificControlsWidget(ft.Card):
    """Widget responsible for presenting specific traffic light controls and schedule actions."""

    def __init__(
        self,
        control_client: ControlClient,
        locale_manager: LocaleManager,
        security_ui=None,
        on_close: Callable[[], None] = None,
        on_specific_command: Callable[[str, str], None] = None,
    ):
        super().__init__(elevation=4, visible=False, animate_opacity=300)

        self.locale_manager = locale_manager
        self.security_ui = security_ui
        self.on_close = on_close
        self.on_specific_command = on_specific_command
        self.handler: SpecificControlsHandler | None = None
        self.control_client = control_client

        self.info_display = SemaphoreInfoDisplayWidget(locale_manager=self.locale_manager)

        # Extracted Schedule Section Component
        self.schedule_section = YellowScheduleSectionWidget(
            locale_manager=self.locale_manager,
            on_quick_enable=self._handle_quick_enable_toggle,
            on_toggle_schedule=self._handle_schedule_toggle,
            on_edit_schedule=self._open_schedule_dialog,
        )

        self.schedule_dialog_manager = YellowScheduleDialog(
            locale_manager=self.locale_manager,
            on_save=self._on_schedule_save,
        )

        self.actions = SemaphoreActionsWidget(
            locale_manager=self.locale_manager, on_action_requested=self._handle_action_request
        )

        self.close_button = ft.IconButton(icon=ft.Icons.CLOSE_ROUNDED, on_click=self.ocultar_controles_semaforo)

        self.content = ft.Container(
            padding=10,
            content=ft.Column(
                [
                    self.info_display,
                    ft.Divider(height=6),
                    self.schedule_section,
                    ft.Divider(height=6),
                    self.actions,
                    self.close_button,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    # ------------------------------------------------------------------
    # Backwards-compatible properties
    # ------------------------------------------------------------------
    @property
    def schedule_container(self) -> ft.Container:
        return self.schedule_section

    @property
    def schedule_icon(self) -> ft.Icon:
        return self.schedule_section.schedule_icon

    @property
    def schedule_title(self) -> ft.Text:
        return self.schedule_section.schedule_title

    @property
    def switch_quick_enable(self) -> ft.Switch:
        return self.schedule_section.switch_quick_enable

    @property
    def schedule_badge(self) -> ft.Container:
        return self.schedule_section.schedule_badge

    @property
    def schedule_badge_text(self) -> ft.Text:
        return self.schedule_section.schedule_badge_text

    @property
    def btn_toggle_schedule(self) -> ft.OutlinedButton:
        return self.schedule_section.btn_toggle_schedule

    @property
    def btn_edit_schedule(self) -> ft.OutlinedButton:
        return self.schedule_section.btn_edit_schedule

    @staticmethod
    def _is_valid_time_str(val: str) -> bool:
        """Maintained for backwards-compatibility with existing tests and callers."""
        return YellowScheduleDialog.is_valid_time_str(val)

    def did_mount(self):
        if self.page:
            dialog_manager = ConfirmationDialogManager(self.page, self.locale_manager)
            self.handler = SpecificControlsHandler(
                control_client=self.control_client,
                dialog_manager=dialog_manager,
                locale_manager=self.locale_manager,
                security_ui=self.security_ui,
                on_update_view=self._on_handler_update,
                on_specific_command=self.on_specific_command,
            )
            self.schedule_dialog_manager.mount(self.page)
        self.update_translations(self.locale_manager)
        if self.page:
            self.update()

    def _on_handler_update(self):
        self._update_schedule_display()
        if self.page:
            self.update()

    def _open_schedule_dialog(self, e):
        if not self.handler or not self.page:
            return
        cfg = self.handler.get_raw_schedule_config()
        self.schedule_dialog_manager.open(cfg)

    def _on_schedule_save(self, start: str, end: str, all_semaphores: bool, enabled: bool) -> None:
        if not self.handler:
            return
        self.handler.save_custom_schedule(
            start=start,
            end=end,
            all_semaphores=all_semaphores,
            enabled=enabled,
        )
        self._update_schedule_display()
        if self.page:
            self.update()

    def _handle_quick_enable_toggle(self, e):
        if not self.handler:
            return
        self.handler.toggle_schedule_enabled()
        self._update_schedule_display()
        if self.page:
            self.update()

    def update_translations(self, lm: LocaleManager):
        self.close_button.tooltip = lm.get_string("dashboard_view.close_panel_tooltip")
        self.schedule_section.update_translations(lm)
        self.info_display.update_translations(lm)
        self.actions.update_translations(lm)
        self._update_schedule_display()
        if self.page:
            self.update()

    def _update_schedule_display(self):
        if not self.handler:
            return
        status = self.handler.get_schedule_status()
        self.schedule_section.update_display(status)

    def _handle_schedule_toggle(self, e):
        if not self.handler:
            return
        self.handler.toggle_schedule_for_current_semaphore()
        self._update_schedule_display()
        if self.page:
            self.update()

    def exibir_controles_semaforo(self, semaphore_id: str, semaphore_data: Dict, phase: str, mode: str):
        if not self.handler:
            return
        self.handler.open_for_semaphore(semaphore_id, semaphore_data)

        is_editable = True
        override_state = self.handler.get_current_override_state()

        self.info_display.update_info(semaphore_id, phase, semaphore_data)
        self._update_schedule_display()

        self.actions.set_active_state(override_state)
        self.actions.alert_button.disabled = not is_editable
        self.actions.deactivate_button.disabled = not is_editable

        self.visible = True
        if self.page:
            self.update()

    def _handle_action_request(self, action: str):
        if not self.handler:
            return
        self.handler.request_confirmation(action)

    def ocultar_controles_semaforo(self, e=None):
        self.visible = False
        if self.page:
            self.update()
        if self.on_close:
            self.on_close()
