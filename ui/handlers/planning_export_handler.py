# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# File: ui/handlers/planning_export_handler.py
# Author: Gabriel Moraes
# Date: August 13, 2026

import base64
import logging
import os
from typing import Optional, Tuple

from ui.formatting.report_exporter import ReportExporter
from ui.handlers.locale_manager import LocaleManager


class PlanningExportHandler:
    """
    Dedicated Service Handler for Planning Report File I/O and DOCX Exporting.
    Single Responsibility: Manages map image resolution, Base64 encoding, and report export execution.
    """

    @staticmethod
    def load_scenario_map_base64(scenario_dir: Optional[str]) -> str:
        """Resolves planning map PNG image path and returns Base64 encoded string."""
        if not scenario_dir:
            return ""

        map_path = os.path.join(scenario_dir, "map_planning.png")
        if not os.path.exists(map_path):
            map_path = os.path.join(scenario_dir, "maps", "map_planning.png")

        if os.path.exists(map_path):
            try:
                with open(map_path, "rb") as img_file:
                    return base64.b64encode(img_file.read()).decode("utf-8")
            except Exception as ex:
                logging.error(f"[PlanningExportHandler] Error reading map PNG: {ex}")
                return ""
        return ""

    @classmethod
    def export_report(
        cls,
        page,
        locale_manager: LocaleManager,
        save_path: str,
        report_content: str,
        scenario_dir: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Orchestrates full report generation pipeline to destination file path.
        Returns tuple of (success_boolean, status_message).
        """
        if not save_path.lower().endswith(".docx"):
            save_path += ".docx"

        try:
            image_base64 = cls.load_scenario_map_base64(scenario_dir)

            success = ReportExporter.export_report(
                page=page,
                locale_manager=locale_manager,
                save_path=save_path,
                image_base64=image_base64,
                text_content=report_content,
                results_dir=scenario_dir if scenario_dir else "",
                mode="PLANNING",
                agent_id="CARINA SAS Engine",
            )

            if success:
                msg = locale_manager.get_string(
                    "planning_view.status_report_saved", default="Relatório salvo com sucesso."
                )
                return True, msg
            else:
                return False, "Erro ao exportar relatório DOCX."
        except Exception as ex:
            logging.error(f"[PlanningExportHandler] Report export failed: {ex}", exc_info=True)
            return False, f"Erro ao salvar arquivo: {ex}"
