# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import time
from typing import Callable, Dict, Optional, Tuple

from ui.clients.infrastructure_client import InfrastructureClient
from ui.handlers.locale_manager import LocaleManager
from ui.handlers.planning_export_handler import PlanningExportHandler


class PlanningController:
    """
    Controller responsible for managing urban analysis state and
    orchestrating communication with infrastructure and export clients.
    """

    def __init__(
        self,
        locale_manager: LocaleManager,
        control_client=None,
        sas_result_queue=None,
        client=None,
        on_complete_callback: Optional[Callable[[dict], None]] = None,
    ):
        self.locale_manager = locale_manager
        self.control_client = control_client
        self.on_complete_callback = on_complete_callback

        self.client = client or InfrastructureClient(
            on_complete_callback=self._handle_analysis_complete, sas_result_queue=sas_result_queue
        )

        self.last_report_content: Optional[str] = None
        self.last_scenario_dir: Optional[str] = None
        self.is_analyzing: bool = False

    def _handle_analysis_complete(self, response: dict):
        if self.on_complete_callback:
            self.on_complete_callback(response)

    def trigger_analysis(self) -> float:
        """
        Resets current state and initiates a new analysis request.
        Returns trigger time (trigger_time).
        """
        trigger_time = time.time()
        self.is_analyzing = True
        self.last_report_content = None
        self.last_scenario_dir = None

        if self.control_client:
            try:
                self.control_client.trigger_analysis()
            except Exception as ex:
                logging.error(f"[PLANNING_CONTROLLER] Error triggering analysis: {ex}", exc_info=True)

        self.client.start_fetching_latest_analysis(trigger_time=trigger_time)
        return trigger_time

    def process_analysis_response(self, response: dict) -> Dict:
        """
        Processes analysis response, updating internal state and returning
        a structured dictionary with state updates for the View.
        """
        self.is_analyzing = False

        if response.get("status") == "error":
            self.last_report_content = None
            return {
                "status": "error",
                "message": response.get("message", "Erro desconhecido."),
                "report_content": None,
                "analysis_results": {},
            }

        self.last_report_content = response.get("report_content")
        self.last_scenario_dir = response.get("scenario_dir")
        recs = response.get("analysis_results", {})
        significant_change = response.get("significant_change")

        return {
            "status": "success",
            "report_content": self.last_report_content,
            "scenario_dir": self.last_scenario_dir,
            "analysis_results": recs,
            "significant_change": significant_change,
        }

    def export_report(self, page, save_path: str) -> Tuple[bool, str]:
        """
        Exports current report using PlanningExportHandler.
        """
        if not self.last_report_content or not save_path:
            return False, "Nenhum relatório disponível para salvar."

        return PlanningExportHandler.export_report(
            page=page,
            locale_manager=self.locale_manager,
            save_path=save_path,
            report_content=self.last_report_content,
            scenario_dir=self.last_scenario_dir,
        )
