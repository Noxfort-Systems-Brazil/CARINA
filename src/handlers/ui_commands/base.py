# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from dataclasses import dataclass
from typing import Any, Callable, Optional, Protocol

from utils.audit_logger import AuditLogger


@dataclass
class UICommandContext:
    """Context object shared across UI command handlers."""

    locale_manager: Any
    override_manager: Any
    failsafe_manager: Any
    security_manager: Any
    sds_data_queue: Any
    sas_data_queue: Any
    mfd_trigger_queue: Any
    yellow_schedule_manager: Any
    audit_logger: AuditLogger
    last_auth_user: str = "Sistema"
    on_ui_ready: Optional[Callable] = None

    def get_settings_manager(self):
        try:
            import src.handlers.ui_command_handler as uic
        except ImportError:
            import handlers.ui_command_handler as uic

        settings_cls = getattr(uic, "SettingsManager", None)
        if settings_cls is not None:
            return settings_cls()
        from utils.settings_manager import SettingsManager

        return SettingsManager()


class UICommandHandlerStrategy(Protocol):
    """Protocol for specialized UI command handlers."""

    def handle(
        self,
        cmd_type: str,
        payload: dict,
        context: UICommandContext,
        sumo_conn: Any,
        override_commands_buffer: list,
    ) -> bool:
        ...
