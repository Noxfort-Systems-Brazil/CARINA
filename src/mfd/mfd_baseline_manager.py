# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later
import json
import logging
import os


class MFDReportBaselineManager:
    """Manages saving and loading of baseline MFD analysis files (raw, unformatted values)."""

    @staticmethod
    def load_baselines(
        scenario_results_dir: str = None, scenario_name: str = None, db_manager=None
    ) -> tuple[dict, dict]:
        last_data = {}
        first_data = {}

        if not scenario_name and scenario_results_dir:
            scenario_name = os.path.basename(os.path.normpath(scenario_results_dir))

        if db_manager is not None and scenario_name:
            try:
                db_last, db_first = db_manager.get_mfd_analysis_baselines(scenario_name)
                if db_last:
                    last_data = db_last
                if db_first:
                    first_data = db_first
            except Exception as e:
                logging.warning(f"[MFD_BASELINE_MANAGER] Failed to load baselines from database: {e}", exc_info=True)

        # Fallback to local files if not fully loaded from database
        if scenario_results_dir:
            last_analysis_path = os.path.join(scenario_results_dir, "mfd_last_analysis.json")
            first_analysis_path = os.path.join(scenario_results_dir, "mfd_first_analysis.json")

            if not last_data and os.path.exists(last_analysis_path):
                try:
                    with open(last_analysis_path, "r", encoding="utf-8") as f:
                        last_data = json.load(f)
                except Exception as e:
                    logging.warning(f"[MFD_BASELINE_MANAGER] Failed to load previous analysis: {e}", exc_info=True)

            if not first_data and os.path.exists(first_analysis_path):
                try:
                    with open(first_analysis_path, "r", encoding="utf-8") as f:
                        first_data = json.load(f)
                except Exception as e:
                    logging.warning(f"[MFD_BASELINE_MANAGER] Failed to load first analysis baseline: {e}", exc_info=True)

        return last_data, first_data

    @staticmethod
    def save_baselines(
        scenario_results_dir: str = None,
        current_analysis_snapshot: dict = None,
        scenario_name: str = None,
        db_manager=None,
    ) -> None:
        if not current_analysis_snapshot:
            return

        if not scenario_name and scenario_results_dir:
            scenario_name = os.path.basename(os.path.normpath(scenario_results_dir))

        # Save to Database as primary storage
        if db_manager is not None and scenario_name:
            try:
                db_manager.save_mfd_analysis_baselines(scenario_name, current_analysis_snapshot)
            except Exception as e:
                logging.error(f"[MFD_BASELINE_MANAGER] Failed to save baselines in database: {e}", exc_info=True)

        # Save local JSON file backups
        if scenario_results_dir:
            last_analysis_path = os.path.join(scenario_results_dir, "mfd_last_analysis.json")
            first_analysis_path = os.path.join(scenario_results_dir, "mfd_first_analysis.json")

            # Overwrite mfd_last_analysis.json
            try:
                with open(last_analysis_path, "w", encoding="utf-8") as f:
                    json.dump(current_analysis_snapshot, f, indent=4)
            except Exception as e:
                logging.error(f"[MFD_BASELINE_MANAGER] Failed to save current analysis: {e}", exc_info=True)

            # Save first analysis ONLY if it does not exist locally
            if not os.path.exists(first_analysis_path):
                try:
                    with open(first_analysis_path, "w", encoding="utf-8") as f:
                        json.dump(current_analysis_snapshot, f, indent=4)
                    logging.info("[MFD_BASELINE_MANAGER] First analysis baseline saved.")
                except Exception as e:
                    logging.error(f"[MFD_BASELINE_MANAGER] Failed to save first analysis baseline: {e}", exc_info=True)
