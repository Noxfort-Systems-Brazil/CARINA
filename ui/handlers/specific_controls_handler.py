# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Defines the SpecificControlsHandler.
"""

import logging
from typing import Any, Callable, Dict

from ui.clients.control_client import ControlClient
from ui.dialogs.confirmation_dialog_manager import ConfirmationDialogManager
from ui.handlers.locale_manager import LocaleManager


class SpecificControlsHandler:
    """
    The non-visual brain that manages the logic for the specific
    controls panel of a traffic light.
    """

    def __init__(
        self,
        control_client: ControlClient,
        dialog_manager: ConfirmationDialogManager,
        locale_manager: LocaleManager,  # <-- CHANGE 1: Added the parameter
        security_ui=None,
        on_update_view: Callable[[], None] = None,
        on_specific_command: Callable[[str, str], None] = None,
    ):
        self.control_client = control_client
        self.dialog_manager = dialog_manager
        self.locale_manager = locale_manager  # <-- CHANGE 2: Stored
        self.security_ui = security_ui
        self.on_update_view = on_update_view
        self.on_specific_command = on_specific_command

        self.current_semaphore_id: str | None = None
        self.override_states: Dict[str, str] = {}
        self._cached_schedule_mgr = None
        self._last_schedule_fetch_time = 0.0
        self._cache_ttl = 2.0

    def open_for_semaphore(self, semaphore_id: str, semaphore_data: Dict):
        self.current_semaphore_id = semaphore_id

    def get_current_override_state(self) -> str:
        return self.override_states.get(self.current_semaphore_id, "NORMAL")

    def execute_confirmed_action(self, action: str):
        if not self.current_semaphore_id:
            return

        def _execute():
            self.override_states[self.current_semaphore_id] = action
            self.control_client.set_semaphore_override(self.current_semaphore_id, action)
            if self.on_specific_command:
                self.on_specific_command(self.current_semaphore_id, action)
            if self.on_update_view:
                self.on_update_view()

        if action in ["ALERT", "OFF"] and self.security_ui:
            self.security_ui.request_auth(on_success=_execute)
        else:
            _execute()

    def request_confirmation(self, action: str):
        """Uses locale_manager to create and display a translated confirmation dialog."""
        if not self.current_semaphore_id:
            return

        action_text_map = {
            "ALERT": self.locale_manager.get_string("dialogs.specific_action_alert").format(
                id=self.current_semaphore_id
            ),
            "OFF": self.locale_manager.get_string("dialogs.specific_action_off").format(id=self.current_semaphore_id),
            "NORMAL": self.locale_manager.get_string("dialogs.specific_action_normal").format(
                id=self.current_semaphore_id
            ),
        }

        template = self.locale_manager.get_string("dialogs.confirm_specific_action_content")
        content_text = template.format(action_text=action_text_map.get(action, "..."))

        title = self.locale_manager.get_string("dialogs.confirm_action_title")

        self.dialog_manager.show(
            title=title, content=content_text, on_confirm=lambda: self.execute_confirmed_action(action)
        )

    def _get_or_load_schedule_mgr(self, force_refresh: bool = False):
        import time
        now = time.time()
        if force_refresh or self._cached_schedule_mgr is None or (now - self._last_schedule_fetch_time) > self._cache_ttl:
            try:
                from src.utils.settings_manager import SettingsManager
                from src.controller.yellow_schedule_manager import YellowScheduleManager

                sm = SettingsManager()
                cfg = sm.load_settings()
                self._cached_schedule_mgr = YellowScheduleManager(cfg)
                self._last_schedule_fetch_time = now
            except Exception as e:
                logging.debug(f"[SpecificControlsHandler] Error loading YellowScheduleManager: {e}")
        return self._cached_schedule_mgr

    def get_schedule_status(self) -> Dict[str, Any]:
        """Returns schedule state information for the current semaphore."""
        try:
            mgr = self._get_or_load_schedule_mgr()
            if not mgr:
                return {
                    "enabled": False,
                    "start": "23:00",
                    "end": "05:00",
                    "is_all": False,
                    "is_scheduled": False,
                    "is_active_now": False,
                }

            is_enabled = mgr.enabled
            is_window_active = mgr.is_active_now()
            is_all = mgr.all_semaphores
            is_scheduled = mgr.is_semaphore_scheduled(self.current_semaphore_id or "")

            return {
                "enabled": is_enabled,
                "start": mgr.start_time.strftime("%H:%M"),
                "end": mgr.end_time.strftime("%H:%M"),
                "is_all": is_all,
                "is_scheduled": is_scheduled,
                "is_active_now": is_window_active and (is_all or is_scheduled),
            }
        except Exception as e:
            logging.debug(f"[SpecificControlsHandler] Error getting schedule status: {e}")
            return {
                "enabled": False,
                "start": "23:00",
                "end": "05:00",
                "is_all": False,
                "is_scheduled": False,
                "is_active_now": False,
            }

    def get_raw_schedule_config(self) -> Dict[str, Any]:
        """Returns the full schedule configuration dictionary."""
        mgr = self._get_or_load_schedule_mgr(force_refresh=True)
        if not mgr:
            return {
                "yellow_schedule_enabled": False,
                "yellow_schedule_start": "23:00",
                "yellow_schedule_end": "05:00",
                "yellow_schedule_all_semaphores": False,
                "yellow_schedule_semaphores": "",
            }
        return {
            "yellow_schedule_enabled": mgr.enabled,
            "yellow_schedule_start": mgr.start_time.strftime("%H:%M"),
            "yellow_schedule_end": mgr.end_time.strftime("%H:%M"),
            "yellow_schedule_all_semaphores": mgr.all_semaphores,
            "yellow_schedule_semaphores": ", ".join(sorted(list(mgr.semaphores))),
        }

    def toggle_schedule_enabled(self) -> bool:
        """Toggles the global yellow schedule enabled state."""
        try:
            from src.utils.settings_manager import SettingsManager

            mgr = self._get_or_load_schedule_mgr(force_refresh=True)
            new_enabled = not (mgr.enabled if mgr else False)

            payload = {"yellow_schedule_enabled": new_enabled}
            sm = SettingsManager()
            sm.save_settings(payload)
            self.control_client.set_yellow_schedule(payload)

            self._cached_schedule_mgr = None
            if self.on_update_view:
                self.on_update_view()
            return new_enabled
        except Exception as e:
            logging.error(f"[SpecificControlsHandler] Error toggling schedule enabled: {e}", exc_info=True)
            return False

    def save_custom_schedule(
        self,
        start: str,
        end: str,
        all_semaphores: bool = None,
        enabled: bool = None,
    ) -> bool:
        """Saves custom schedule parameters and dispatches update."""
        try:
            from src.utils.settings_manager import SettingsManager

            payload: Dict[str, Any] = {
                "yellow_schedule_start": start.strip(),
                "yellow_schedule_end": end.strip(),
            }
            if all_semaphores is not None:
                payload["yellow_schedule_all_semaphores"] = all_semaphores
            if enabled is not None:
                payload["yellow_schedule_enabled"] = enabled

            sm = SettingsManager()
            sm.save_settings(payload)
            self.control_client.set_yellow_schedule(payload)

            self._cached_schedule_mgr = None
            if self.on_update_view:
                self.on_update_view()
            return True
        except Exception as e:
            logging.error(f"[SpecificControlsHandler] Error saving custom schedule: {e}", exc_info=True)
            return False

    def toggle_schedule_for_current_semaphore(self) -> bool:
        """Toggles current semaphore in the schedule and dispatches command."""
        if not self.current_semaphore_id:
            return False

        try:
            from src.utils.settings_manager import SettingsManager

            mgr = self._get_or_load_schedule_mgr(force_refresh=True)
            included = mgr.toggle_semaphore(self.current_semaphore_id)

            # Persist to settings.ini
            new_sem_str = ", ".join(sorted(list(mgr.semaphores)))
            sm = SettingsManager()
            sm.save_settings({"yellow_schedule_semaphores": new_sem_str})

            # Send IPC command to backend
            self.control_client.toggle_semaphore_yellow_schedule(self.current_semaphore_id)

            self._cached_schedule_mgr = None
            if self.on_update_view:
                self.on_update_view()

            return included
        except Exception as e:
            logging.error(f"[SpecificControlsHandler] Error toggling schedule: {e}", exc_info=True)
            return False

