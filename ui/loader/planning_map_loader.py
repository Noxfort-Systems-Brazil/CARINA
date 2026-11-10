# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Defines the PlanningMapLoader.

This client has the sole responsibility of asynchronously finding
the path to the latest planning map image file, without blocking the UI main thread.
"""

import logging
import os
import threading
import time
from typing import Callable


class PlanningMapLoader:
    """
    Searches for the planning map file in a separate thread.
    """

    def __init__(self, on_complete_callback: Callable[[str | None], None]):
        """
        Initializes the loader.

        Args:
            on_complete_callback: The function to be called when search completes.
                                  Receives the file path or None.
        """
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.on_complete = on_complete_callback

    def _find_latest_map_image_path(self) -> str | None:
        """Finds the expected path for the latest map image."""
        try:
            from src.utils.paths import get_base_output_dir

            results_dir = os.path.join(get_base_output_dir(), "results")
            if not os.path.exists(results_dir):
                return None

            ignored_dirs = {"database"}
            all_scenarios = [
                d
                for d in os.listdir(results_dir)
                if os.path.isdir(os.path.join(results_dir, d)) and d not in ignored_dirs
            ]
            if not all_scenarios:
                return None

            latest_scenario_dir_name = max(all_scenarios, key=lambda d: os.path.getmtime(os.path.join(results_dir, d)))
            maps_dir = os.path.join(results_dir, latest_scenario_dir_name, "maps")

            planning_map_path = os.path.join(maps_dir, "map_planning.png")
            return planning_map_path if os.path.exists(planning_map_path) else None

        except Exception as e:
            logging.error(f"[PlanningMapLoader] Erro ao procurar imagem do mapa: {e}", exc_info=True)
            return None

    def _loader_thread_target(self):
        """
        Thread target: Searches repeatedly for the map file and then
        calls the callback with the result.
        """
        logging.info("[PlanningMapLoader] Iniciando busca em segundo plano pelo mapa de planejamento...")
        map_path = None
        # Try for 60 seconds (20 attempts 3 seconds apart)
        for i in range(20):
            path = self._find_latest_map_image_path()
            if path:
                logging.info(f"[PlanningMapLoader] Mapa encontrado na tentativa {i+1}.")
                map_path = path
                break
            time.sleep(3)

        if not map_path:
            logging.warning("[PlanningMapLoader] Tempo de busca esgotado. Mapa de planejamento não foi encontrado.")

        # Calls the callback with the result (the path or None)
        if self.on_complete:
            self.on_complete(map_path)

    def start_loading(self):
        """
        Starts searching for the map file in a new thread.
        Returns immediately.
        """
        thread = threading.Thread(target=self._loader_thread_target, daemon=True)
        thread.start()
