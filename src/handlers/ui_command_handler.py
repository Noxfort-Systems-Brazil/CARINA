# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import Any, List

from src.handlers.ui_commands.analysis_command_handler import AnalysisCommandHandler
from src.handlers.ui_commands.base import UICommandContext, UICommandHandlerStrategy
from src.handlers.ui_commands.monitor_command_handler import MonitorCommandHandler
from src.handlers.ui_commands.override_command_handler import OverrideCommandHandler
from src.handlers.ui_commands.security_command_handler import SecurityCommandHandler
from src.handlers.ui_commands.settings_command_handler import SettingsCommandHandler
from src.handlers.ui_commands.yellow_schedule_command_handler import YellowScheduleCommandHandler
from src.utils.audit_logger import AuditLogger
from src.utils.settings_manager import SettingsManager


class UICommandHandler:
    """
    Dispatcher for commands incoming from the Front-End (UI).
    Coordinates specialized command strategies following SOLID principles.
    """

    def __init__(
        self,
        locale_manager: Any,
        override_manager: Any,
        failsafe_manager: Any,
        security_manager: Any,
        sds_data_queue: Any,
        sas_data_queue: Any = None,
        mfd_trigger_queue: Any = None,
        yellow_schedule_manager: Any = None,
    ):
        self.context = UICommandContext(
            locale_manager=locale_manager,
            override_manager=override_manager,
            failsafe_manager=failsafe_manager,
            security_manager=security_manager,
            sds_data_queue=sds_data_queue,
            sas_data_queue=sas_data_queue,
            mfd_trigger_queue=mfd_trigger_queue,
            yellow_schedule_manager=yellow_schedule_manager,
            audit_logger=AuditLogger(),
            last_auth_user="Sistema",
            on_ui_ready=None,
        )

        self.handlers: List[UICommandHandlerStrategy] = [
            SettingsCommandHandler(),
            SecurityCommandHandler(),
            OverrideCommandHandler(),
            MonitorCommandHandler(),
            AnalysisCommandHandler(),
            YellowScheduleCommandHandler(),
        ]

    @property
    def locale_manager(self):
        return self.context.locale_manager

    @property
    def override_manager(self):
        return self.context.override_manager

    @property
    def failsafe_manager(self):
        return self.context.failsafe_manager

    @property
    def security_manager(self):
        return self.context.security_manager

    @property
    def sds_data_queue(self):
        return self.context.sds_data_queue

    @property
    def sas_data_queue(self):
        return self.context.sas_data_queue

    @property
    def mfd_trigger_queue(self):
        return self.context.mfd_trigger_queue

    @property
    def yellow_schedule_manager(self):
        return self.context.yellow_schedule_manager

    @property
    def audit_logger(self):
        return self.context.audit_logger

    @property
    def last_auth_user(self):
        return self.context.last_auth_user

    @last_auth_user.setter
    def last_auth_user(self, value: str):
        self.context.last_auth_user = value

    @property
    def on_ui_ready(self):
        return self.context.on_ui_ready

    @on_ui_ready.setter
    def on_ui_ready(self, cb):
        self.context.on_ui_ready = cb

    def set_ui_ready_callback(self, cb):
        self.context.on_ui_ready = cb

    def process(self, command: dict, sumo_conn: Any, override_commands_buffer: list) -> None:
        lm = self.context.locale_manager
        cmd_type = command.get("type")
        payload = command.get("payload", {})

        logging.info(lm.get_string("request_processor.ui_command.received", type=cmd_type))

        handled = False
        for handler in self.handlers:
            if handler.handle(cmd_type, payload, self.context, sumo_conn, override_commands_buffer):
                handled = True
                break

        if not handled:
            logging.warning(f"[RequestProcessor] Comando UI desconhecido recebido: {cmd_type}")
