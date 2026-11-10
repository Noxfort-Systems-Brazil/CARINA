# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import os

from rendering.static_map_renderer import StaticMapRenderer


class SASPlanningMapGenerator:
    """
    Handles recommendation icon mapping and rendering of static planning maps.
    """

    def __init__(self, locale_manager):
        self.locale_manager = locale_manager
        self.map_renderer = StaticMapRenderer(self.locale_manager)

    def generate_map(self, analysis_results: dict, net_file_path: str, scenario_dir: str):
        """Maps recommendation icons and renders map_planning.png."""
        lm = self.locale_manager
        if not scenario_dir or not os.path.exists(scenario_dir):
            logging.error("[SAS_MAP_GENERATOR] Invalid scenario directory. Cannot generate planning map.")
            return

        if not net_file_path:
            logging.warning("[SAS_MAP_GENERATOR] Net file path not available. Planning map skipped.")
            return

        logging.info(lm.get_string("sas_engine.map.generating"))

        icon_requests = {}
        for j_id, r in analysis_results.items():
            rec_str = r.get("recommendation", "").lower()
            if "adicionar" in rec_str or "add" in rec_str:
                icon_requests[j_id] = "add"
            elif "remover" in rec_str or "remove" in rec_str:
                icon_requests[j_id] = "remove"
            elif "não sinalizado" in rec_str or "no_signal" in rec_str or "unsignalized" in rec_str:
                icon_requests[j_id] = "no_signal"
            else:
                icon_requests[j_id] = "existing"

        self.map_renderer.create_map_with_icons(
            net_file_path=net_file_path,
            scenario_results_dir=scenario_dir,
            icon_requests=icon_requests,
            output_filename="map_planning.png",
        )
