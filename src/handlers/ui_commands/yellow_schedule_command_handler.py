# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import Any

from src.handlers.ui_commands.base import UICommandContext


class YellowScheduleCommandHandler:
    """Handles schedule configuration for intermittent yellow operation."""

    def handle(
        self,
        cmd_type: str,
        payload: dict,
        context: UICommandContext,
        sumo_conn: Any,
        override_commands_buffer: list,
    ) -> bool:
        if cmd_type == "toggle_yellow_schedule_semaphore":
            semaphore_id = payload.get("semaphore_id", "")
            if context.yellow_schedule_manager and semaphore_id:
                included = context.yellow_schedule_manager.toggle_semaphore(semaphore_id)
                settings_manager = context.get_settings_manager()
                current_settings = settings_manager.load_settings()
                current_settings["yellow_schedule_semaphores"] = ", ".join(
                    sorted(list(context.yellow_schedule_manager.semaphores))
                )
                settings_manager.save_settings(current_settings)
                context.yellow_schedule_manager.tick(context.override_manager, sumo_conn)
                context.audit_logger.log_action(
                    context.last_auth_user,
                    "TOGGLE_YELLOW_SCHEDULE",
                    f"{semaphore_id} -> {'Incluído' if included else 'Removido'}",
                )
                if context.sds_data_queue:
                    try:
                        context.sds_data_queue.put(("yellow_schedule_update", context.yellow_schedule_manager.get_status()))
                    except Exception:
                        pass
                logging.info(
                    f"[UICommandHandler] Semáforo {semaphore_id} {'incluído no' if included else 'removido do'} agendamento de amarelo intermitente."
                )
            return True

        elif cmd_type == "set_yellow_schedule":
            if context.yellow_schedule_manager and isinstance(payload, dict):
                context.yellow_schedule_manager.load_config(payload)
                settings_manager = context.get_settings_manager()
                settings_manager.save_settings(payload)
                context.yellow_schedule_manager.tick(context.override_manager, sumo_conn)
                context.audit_logger.log_action(context.last_auth_user, "SET_YELLOW_SCHEDULE", "Programação atualizada")
                if context.sds_data_queue:
                    try:
                        context.sds_data_queue.put(("yellow_schedule_update", context.yellow_schedule_manager.get_status()))
                    except Exception:
                        pass
                logging.info("[UICommandHandler] Agendamento de amarelo intermitente atualizado com sucesso.")
            return True

        return False
