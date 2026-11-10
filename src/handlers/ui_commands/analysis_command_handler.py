# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import Any

from src.handlers.ui_commands.base import UICommandContext


class AnalysisCommandHandler:
    """Handles commands triggering background simulations, SAS planning analysis, and MFD evaluations."""

    def handle(
        self,
        cmd_type: str,
        payload: dict,
        context: UICommandContext,
        sumo_conn: Any,
        override_commands_buffer: list,
    ) -> bool:
        if cmd_type == "carina_ready":
            logging.info("✅ [RequestProcessor] Comando de 'carina_ready' recebido da Interface Gráfica.")
            if context.on_ui_ready and callable(context.on_ui_ready):
                context.on_ui_ready()
            return True

        elif cmd_type == "trigger_analysis":
            logging.info("[UICommandHandler] Recebido comando para forçar análise de planejamento.")
            if context.sas_data_queue:
                context.sas_data_queue.put(("trigger_analysis", {}))
            else:
                logging.warning("[UICommandHandler] sas_data_queue não disponível para forçar análise.")
            return True

        elif cmd_type == "trigger_mfd_analysis":
            logging.info("[UICommandHandler] Recebido comando para forçar análise MFD.")
            if context.mfd_trigger_queue:
                context.mfd_trigger_queue.put(("trigger_mfd", {}))
            else:
                logging.warning("[UICommandHandler] mfd_trigger_queue não disponível para forçar análise MFD.")
            return True

        return False
