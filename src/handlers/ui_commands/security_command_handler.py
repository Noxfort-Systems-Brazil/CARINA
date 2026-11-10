# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import Any

from src.handlers.ui_commands.base import UICommandContext


class SecurityCommandHandler:
    """Handles operator authentication, account management, audit logs, and lockdown checks."""

    def handle(
        self,
        cmd_type: str,
        payload: dict,
        context: UICommandContext,
        sumo_conn: Any,
        override_commands_buffer: list,
    ) -> bool:
        if cmd_type == "authenticate":
            username = payload.get("username")
            password = payload.get("password")
            success, role_or_msg = context.security_manager.authenticate(username, password)
            if success:
                context.last_auth_user = username
                context.audit_logger.log_action(username, "LOGIN_SUCCESS", f"Sessão iniciada como {role_or_msg}")
                context.sds_data_queue.put(("auth_response", {"success": True, "role": role_or_msg}))
            else:
                context.audit_logger.log_action(username or "UNKNOWN", "LOGIN_FAILED", "Falha de autenticação")
                context.sds_data_queue.put(("auth_response", {"success": False, "message": role_or_msg}))

                if hasattr(context.failsafe_manager, "monitor_client") and context.failsafe_manager.monitor_client:
                    msg = context.locale_manager.get_string(
                        "monitor.auth_failure",
                        default="Falha de autenticação detectada para o usuário: {username}",
                        username=username,
                    )
                    context.failsafe_manager.monitor_client.report_incident(
                        category="SOFTWARE", level="WARNING", message=msg
                    )

                if context.security_manager.is_lockdown():
                    logging.critical("[UICommandHandler] Lockdown ativado. Cortando heartbeats físicos.")
                    override_commands_buffer.append({"semaphore_id": "ALL", "state": "SHUTDOWN"})
                    context.sds_data_queue.put(("lockdown_event", {"active": True}))

                    if hasattr(context.failsafe_manager, "monitor_client") and context.failsafe_manager.monitor_client:
                        msg = context.locale_manager.get_string(
                            "monitor.lockdown_active",
                            default="LOCKDOWN de segurança ativado devido a múltiplas falhas de login.",
                        )
                        context.failsafe_manager.monitor_client.report_incident(
                            category="SOFTWARE", level="CRITICAL", message=msg
                        )
            return True

        elif cmd_type == "check_lockdown":
            if context.security_manager.is_lockdown():
                context.sds_data_queue.put(("lockdown_event", {"active": True}))
            return True

        elif cmd_type == "add_user":
            username = payload.get("username")
            password = payload.get("password")
            role = payload.get("role")
            success = context.security_manager.add_user(username, password, role)
            if success:
                context.audit_logger.log_action(context.last_auth_user, "ADD_USER", f"Usuário {username} criado ({role}).")
            context.sds_data_queue.put(("account_response", {"action": "add", "success": success}))
            if success:
                context.sds_data_queue.put(("users_list", {"users": context.security_manager.list_users()}))
            return True

        elif cmd_type == "remove_user":
            username = payload.get("username")
            success = context.security_manager.remove_user(username)
            if success:
                context.audit_logger.log_action(context.last_auth_user, "REMOVE_USER", f"Usuário {username} deletado.")
            context.sds_data_queue.put(("account_response", {"action": "remove", "success": success}))
            if success:
                context.sds_data_queue.put(("users_list", {"users": context.security_manager.list_users()}))
            return True

        elif cmd_type == "list_users":
            users = context.security_manager.list_users()
            context.sds_data_queue.put(("users_list", {"users": users}))
            return True

        elif cmd_type == "get_audit_logs":
            context.sds_data_queue.put(("audit_logs_response", {"logs": context.audit_logger.get_logs()}))
            return True

        return False
