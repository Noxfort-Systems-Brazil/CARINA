# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import logging
import os
from typing import Optional, Tuple


class SASAnalysisCacheManager:
    """
    Handles loading and saving of previous SAS analysis cache snapshots
    for change detection across analysis runs (DB primary + file backup).
    """

    def load_cache(self, db_manager, scenario_name: str, scenario_dir: Optional[str]) -> Tuple[dict, bool]:
        """Loads previous analysis cache snapshot from DB or JSON file fallback."""
        last_analysis_path = os.path.join(scenario_dir, "sas_last_analysis.json") if scenario_dir else None
        last_analysis_cache = {}
        has_previous_report = False

        if db_manager is not None:
            try:
                last_analysis_cache = db_manager.get_sas_analysis_cache(scenario_name)
                if last_analysis_cache:
                    has_previous_report = True
            except Exception as e:
                logging.warning(f"[SAS_CACHE_MANAGER] Failed to load cache from database: {e}", exc_info=True)

        # Fallback to local JSON file if cache was not loaded from DB
        if not last_analysis_cache and last_analysis_path and os.path.exists(last_analysis_path):
            try:
                with open(last_analysis_path, "r", encoding="utf-8") as f:
                    last_analysis_cache = json.load(f)
                has_previous_report = True
            except Exception as e:
                logging.warning(f"[SAS_CACHE_MANAGER] Failed to load cache from file: {e}", exc_info=True)

        return last_analysis_cache, has_previous_report

    def save_cache(self, db_manager, scenario_name: str, scenario_dir: Optional[str], new_cache_data: dict):
        """Saves current analysis cache snapshot into DB and JSON file backup."""
        if not new_cache_data:
            return

        if db_manager is not None:
            try:
                db_manager.save_sas_analysis_cache(scenario_name, new_cache_data)
            except Exception as e:
                logging.error(f"[SAS_CACHE_MANAGER] Failed to save cache into database: {e}", exc_info=True)

        if scenario_dir:
            last_analysis_path = os.path.join(scenario_dir, "sas_last_analysis.json")
            try:
                with open(last_analysis_path, "w", encoding="utf-8") as f:
                    json.dump(new_cache_data, f, indent=4)
            except Exception as e:
                logging.error(f"[SAS_CACHE_MANAGER] Failed to save cache into file: {e}", exc_info=True)
