# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import Any


class WatchdogCommandHandler:
    """
    Handles emergency and failsafe commands produced by the Watchdog System.
    """

    def __init__(self, locale_manager):
        self.locale_manager = locale_manager

    def process(self, command_batch: list, sumo_conn: Any):
        lm = self.locale_manager

        try:
            for command in command_batch:
                cmd_type = command.get("type")
                if cmd_type == "set_program_all":
                    program_id = command.get("value", "0")
                    # Environment adapter should ingest 'set_program_all' as a dict-command if required.
                    logging.warning(
                        f"[RequestProcessor] Comando Watchdog '{cmd_type}' interceptado. Adaptação Agnóstica requisitada."
                    )
        except Exception as e:
            logging.error(lm.get_string("request_processor.watchdog.processing_error", error=e), exc_info=True)
