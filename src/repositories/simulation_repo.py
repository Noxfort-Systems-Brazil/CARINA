# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from src.repositories.analysis_cache_repo import AnalysisCacheRepository

if TYPE_CHECKING:
    from src.database.db_engine import DatabaseEngine
    from src.utils.locale_manager_backend import LocaleManagerBackend


class SimulationRepository:
    """
    Repository for managing simulation runs, episodes, and analysis reports.
    """

    def __init__(self, engine: "DatabaseEngine", locale_manager: "LocaleManagerBackend"):
        self.engine = engine
        self.locale_manager = locale_manager
        self.analysis_cache = AnalysisCacheRepository(self.engine, self.locale_manager)

    def create_simulation_run(self, scenario_name: str) -> Optional[int]:
        """
        Registers a new execution using parameterized queries based on the dialect.
        """
        lm = self.locale_manager
        conn = self.engine.get_connection()
        if not conn:
            return None
        try:
            cursor = conn.cursor()
            start_time = datetime.now()

            if self.engine.db_type == "postgres":
                cursor.execute(
                    "INSERT INTO simulation_runs (start_time, scenario_name) VALUES (%s, %s) RETURNING run_id;",
                    (start_time, scenario_name),
                )
                run_id = cursor.fetchone()[0]
            else:
                cursor.execute(
                    "INSERT INTO simulation_runs (start_time, scenario_name) VALUES (?, ?);",
                    (start_time, scenario_name),
                )
                run_id = cursor.lastrowid

            conn.commit()
            logging.info(lm.get_string("db_manager.create_run.success", scenario=scenario_name))
            return run_id
        except Exception as e:
            logging.error(lm.get_string("db_manager.create_run.error", error=e), exc_info=True)
            return None
        finally:
            if conn:
                conn.close()

    def log_episode(self, run_id: int, episode_number: int, total_reward: float):
        """Saves the metrics for a completed episode to the database."""
        conn = self.engine.get_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            end_time = datetime.now()

            if self.engine.db_type == "postgres":
                cursor.execute(
                    "INSERT INTO episodes (run_id, episode_number, total_reward, end_time) VALUES (%s, %s, %s, %s);",
                    (run_id, episode_number, total_reward, end_time),
                )
            else:
                cursor.execute(
                    "INSERT INTO episodes (run_id, episode_number, total_reward, end_time) VALUES (?, ?, ?, ?);",
                    (run_id, episode_number, total_reward, end_time),
                )
            conn.commit()
        except Exception as e:
            logging.error(
                self.locale_manager.get_string("db_manager.log_episode.error", episode=episode_number, error=e)
            , exc_info=True)
        finally:
            if conn:
                conn.close()

    def log_analysis_report(self, run_id: int, summary: str, report_content: str):
        """Saves an infrastructure analysis report."""
        conn = self.engine.get_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            timestamp = datetime.now()

            if self.engine.db_type == "postgres":
                cursor.execute(
                    "INSERT INTO analysis_reports (run_id, timestamp, summary, report_content) VALUES (%s, %s, %s, %s);",
                    (run_id, timestamp, summary, report_content),
                )
            else:
                cursor.execute(
                    "INSERT INTO analysis_reports (run_id, timestamp, summary, report_content) VALUES (?, ?, ?, ?);",
                    (run_id, timestamp, summary, report_content),
                )
            conn.commit()
        except Exception as e:
            logging.error(self.locale_manager.get_string("db_manager.log_report.error", error=e), exc_info=True)
        finally:
            if conn:
                conn.close()

    # =========================================================================
    # SAS & MFD ANALYSIS CACHE / BASELINES (Delegated to AnalysisCacheRepository)
    # =========================================================================

    def get_sas_analysis_cache(self, scenario_name: str) -> dict:
        """Retrieves SAS analysis cache dictionary from DB for scenario_name."""
        return self.analysis_cache.get_sas_analysis_cache(scenario_name)

    def save_sas_analysis_cache(self, scenario_name: str, cache_data: dict) -> None:
        """Saves or updates SAS analysis cache in DB for scenario_name."""
        self.analysis_cache.save_sas_analysis_cache(scenario_name, cache_data)

    def get_mfd_analysis_baselines(self, scenario_name: str) -> tuple:
        """Retrieves MFD baseline tuples (last_data, first_data) from DB for scenario_name."""
        return self.analysis_cache.get_mfd_analysis_baselines(scenario_name)

    def save_mfd_analysis_baselines(self, scenario_name: str, snapshot: dict) -> None:
        """Saves MFD analysis baselines in DB for scenario_name."""
        self.analysis_cache.save_mfd_analysis_baselines(scenario_name, snapshot)

