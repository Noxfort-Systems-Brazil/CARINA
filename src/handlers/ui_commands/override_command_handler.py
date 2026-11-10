# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import Any

from src.handlers.ui_commands.base import UICommandContext


class OverrideCommandHandler:
    """Handles global operation modes, semaphore manual overrides, and street overrides."""

    def handle(
        self,
        cmd_type: str,
        payload: dict,
        context: UICommandContext,
        sumo_conn: Any,
        override_commands_buffer: list,
    ) -> bool:
        lm = context.locale_manager
        if cmd_type == "set_global_mode":
            new_mode = payload.get("mode", "AUTOMATIC").upper()
            old_mode = context.failsafe_manager.current_operation_mode
            if new_mode != old_mode and new_mode in ["AUTOMATIC", "SEMI_AUTOMATIC", "MANUAL"]:
                logging.info(
                    f"[CONTROLE GLOBAL] Modo de operação alterado de '{old_mode}' para '{new_mode}' pelo operador."
                )
                context.audit_logger.log_action(
                    context.last_auth_user, "GLOBAL_MODE_CHANGE", f"De {old_mode} para {new_mode}"
                )
                context.failsafe_manager.current_operation_mode = new_mode
            elif new_mode != old_mode:
                logging.warning(f"[RequestProcessor] Tentativa de definir modo global inválido: '{new_mode}'")
            return True

        elif cmd_type == "set_semaphore_override":
            semaphore_id = payload.get("semaphore_id", "N/A")
            new_state = payload.get("state", "N/A")
            context.audit_logger.log_action(context.last_auth_user, "OVERRIDE_SEMAPHORE", f"{semaphore_id} -> {new_state}")
            logging.warning(
                lm.get_string(
                    "request_processor.override.manual_intervention", semaphore_id=semaphore_id, state=new_state
                )
            )
            if sumo_conn:
                override_commands_buffer.append(payload)
                context.override_manager.handle_ui_command(payload, sumo_conn)
            else:
                context.override_manager.active_overrides[semaphore_id] = new_state
                if new_state == "NORMAL":
                    context.override_manager.active_overrides.pop(semaphore_id, None)
                context.override_manager._save_state_to_disk()

                if (
                    context.failsafe_manager
                    and context.failsafe_manager.ai_pipe_conn
                    and not context.failsafe_manager.ai_pipe_conn.closed
                ):
                    logging.info(
                        f"[UICommandHandler] Sending manual override for {semaphore_id} ({new_state}) to AI process via pipe."
                    )
                    context.failsafe_manager.ai_pipe_conn.send(
                        ("hardware", "apply_override", (semaphore_id, new_state), {})
                    )
                else:
                    logging.warning(
                        "[UICommandHandler] AI pipe connection is not active/closed. Manual override not forwarded."
                    )
            return True

        elif cmd_type == "set_street_override":
            street_id = payload.get("street_id", "N/A")
            new_state = payload.get("state", "N/A")
            context.audit_logger.log_action(context.last_auth_user, "OVERRIDE_STREET", f"{street_id} -> {new_state}")
            logging.warning(f"[UICommandHandler] Intervenção manual na rua '{street_id}': {new_state}")
            context.override_manager.handle_street_command(payload)
            return True

        return False
