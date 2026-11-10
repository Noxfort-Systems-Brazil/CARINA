# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import Any

from src.handlers.ui_commands.base import UICommandContext


class MonitorCommandHandler:
    """Handles external telemetry monitor and hardware connection toggling."""

    def handle(
        self,
        cmd_type: str,
        payload: dict,
        context: UICommandContext,
        sumo_conn: Any,
        override_commands_buffer: list,
    ) -> bool:
        if cmd_type == "set_monitor_connection":
            enabled = payload.get("enabled", False)
            host = payload.get("host", "localhost")
            is_enabled = (
                str(enabled).strip().lower() in ("true", "1", "yes", "on")
                if isinstance(enabled, str)
                else bool(enabled)
            )

            if hasattr(context.failsafe_manager, "monitor_client") and context.failsafe_manager.monitor_client:
                if is_enabled:
                    context.failsafe_manager.monitor_client.connect_manual(host)
                    logging.info(f"[RequestProcessor] Monitor manually CONNECTED to {host}")
                else:
                    context.failsafe_manager.monitor_client.disconnect_manual()
                    logging.info("[RequestProcessor] Monitor manually DISCONNECTED.")
            else:
                logging.warning("[RequestProcessor] MonitorClient interface not found.")

            # Auto-Save connection intent for the next session
            settings_manager = context.get_settings_manager()
            current_settings = settings_manager.load_settings()
            current_settings["monitor_enabled"] = "True" if is_enabled else "False"
            current_settings["monitor_mqtt_host"] = host
            settings_manager.save_settings(current_settings)
            logging.info("[RequestProcessor] Monitor connection state permanently saved to settings.ini.")
            return True

        elif cmd_type == "set_hardware_connection":
            # Pass this through a special queue or we can handle it in request_processor
            return True

        return False
