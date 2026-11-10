# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import Any

from src.handlers.ui_commands.base import UICommandContext


class SettingsCommandHandler:
    """Handles global and module-specific settings persistence commands."""

    def handle(
        self,
        cmd_type: str,
        payload: dict,
        context: UICommandContext,
        sumo_conn: Any,
        override_commands_buffer: list,
    ) -> bool:
        if cmd_type != "save_settings":
            return False

        lm = context.locale_manager
        settings_manager = context.get_settings_manager()
        settings_manager.save_settings(payload)

        # Synchronize MonitorClient with newly saved settings
        mon_enabled_raw = None
        mon_host_raw = None
        if isinstance(payload, dict):
            if "EXTERNAL_MONITOR" in payload and isinstance(payload["EXTERNAL_MONITOR"], dict):
                mon_enabled_raw = payload["EXTERNAL_MONITOR"].get("monitor_enabled")
                mon_host_raw = payload["EXTERNAL_MONITOR"].get("monitor_mqtt_host")
            if mon_enabled_raw is None and "monitor_enabled" in payload:
                mon_enabled_raw = payload.get("monitor_enabled")
            if mon_host_raw is None and "monitor_mqtt_host" in payload:
                mon_host_raw = payload.get("monitor_mqtt_host")

        if (
            mon_enabled_raw is not None
            and hasattr(context.failsafe_manager, "monitor_client")
            and context.failsafe_manager.monitor_client
        ):
            is_enabled = str(mon_enabled_raw).strip().lower() in ("true", "1", "yes", "on")
            if is_enabled:
                target_host = mon_host_raw or getattr(context.failsafe_manager.monitor_client, "host", "localhost")
                context.failsafe_manager.monitor_client.connect_manual(target_host)
                logging.info(
                    f"[UICommandHandler] Monitor synchronized via save_settings: CONNECTED to {target_host}"
                )
            else:
                context.failsafe_manager.monitor_client.disconnect_manual()
                logging.info("[UICommandHandler] Monitor synchronized via save_settings: DISCONNECTED")

        new_lang = None
        if "General" in payload and "language" in payload["General"]:
            new_lang = payload["General"]["language"]
        elif "language" in payload:
            new_lang = payload["language"]

        if new_lang:
            context.locale_manager.load_language(new_lang)

        if context.yellow_schedule_manager and isinstance(payload, dict):
            context.yellow_schedule_manager.load_config(payload)
            context.yellow_schedule_manager.tick(context.override_manager, sumo_conn)
            if context.sds_data_queue:
                try:
                    context.sds_data_queue.put(("yellow_schedule_update", context.yellow_schedule_manager.get_status()))
                except Exception:
                    pass

        context.audit_logger.log_action(context.last_auth_user, "SAVE_SETTINGS", "Configurações Globais alteradas")
        logging.info(lm.get_string("request_processor.ui_command.save_success"))
        return True
