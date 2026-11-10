# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import logging
from typing import TYPE_CHECKING, Optional, Tuple

if TYPE_CHECKING:
    from src.database.db_engine import DatabaseEngine
    from src.utils.locale_manager_backend import LocaleManagerBackend


class AnalysisCacheRepository:
    """
    Repository dedicated to managing SAS analysis cache and MFD baseline caches.
    Follows Single Responsibility Principle (SRP) and Clean Architecture layer isolation.
    """

    def __init__(self, engine: "DatabaseEngine", locale_manager: Optional["LocaleManagerBackend"] = None):
        self.engine = engine
        self.locale_manager = locale_manager

    def get_sas_analysis_cache(self, scenario_name: str) -> dict:
        """Retrieves SAS analysis cache dictionary from DB for scenario_name."""
        if not scenario_name:
            return {}
        conn = self.engine.get_connection()
        if not conn:
            return {}
        try:
            cursor = conn.cursor()
            ph = "%s" if self.engine.db_type == "postgres" else "?"
            cursor.execute(
                f"SELECT metrics_cache FROM sas_analysis_cache WHERE scenario_name = {ph};", (scenario_name,)
            )
            row = cursor.fetchone()
            if row and row[0]:
                data = row[0]
                if isinstance(data, str):
                    return json.loads(data)
                elif isinstance(data, dict):
                    return data
            return {}
        except Exception as e:
            logging.warning(f"[ANALYSIS_CACHE_REPO] Failed to get SAS analysis cache for '{scenario_name}': {e}", exc_info=True)
            return {}
        finally:
            if conn:
                conn.close()

    def save_sas_analysis_cache(self, scenario_name: str, cache_data: dict) -> None:
        """Saves or updates SAS analysis cache in DB for scenario_name."""
        if not scenario_name or not cache_data:
            return
        conn = self.engine.get_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            serialized = json.dumps(cache_data)
            if self.engine.db_type == "postgres":
                query = """
                INSERT INTO sas_analysis_cache (scenario_name, metrics_cache, updated_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (scenario_name)
                DO UPDATE SET metrics_cache = EXCLUDED.metrics_cache, updated_at = NOW();
                """
                cursor.execute(query, (scenario_name, serialized))
            else:
                query = """
                INSERT INTO sas_analysis_cache (scenario_name, metrics_cache, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT (scenario_name)
                DO UPDATE SET metrics_cache = excluded.metrics_cache, updated_at = CURRENT_TIMESTAMP;
                """
                cursor.execute(query, (scenario_name, serialized))
            conn.commit()
        except Exception as e:
            logging.error(f"[ANALYSIS_CACHE_REPO] Failed to save SAS analysis cache for '{scenario_name}': {e}", exc_info=True)
        finally:
            if conn:
                conn.close()

    def get_mfd_analysis_baselines(self, scenario_name: str) -> Tuple[dict, dict]:
        """Retrieves MFD baseline tuples (last_data, first_data) from DB for scenario_name."""
        last_data, first_data = {}, {}
        if not scenario_name:
            return last_data, first_data
        conn = self.engine.get_connection()
        if not conn:
            return last_data, first_data
        try:
            cursor = conn.cursor()
            ph = "%s" if self.engine.db_type == "postgres" else "?"
            cursor.execute(
                f"SELECT cache_type, metrics_cache FROM mfd_analysis_cache WHERE scenario_name = {ph};",
                (scenario_name,),
            )
            rows = cursor.fetchall()
            for c_type, raw_data in rows:
                parsed = {}
                if isinstance(raw_data, str):
                    parsed = json.loads(raw_data)
                elif isinstance(raw_data, dict):
                    parsed = raw_data
                if c_type == "last":
                    last_data = parsed
                elif c_type == "first":
                    first_data = parsed
            return last_data, first_data
        except Exception as e:
            logging.warning(f"[ANALYSIS_CACHE_REPO] Failed to get MFD analysis baselines for '{scenario_name}': {e}", exc_info=True)
            return {}, {}
        finally:
            if conn:
                conn.close()

    def save_mfd_analysis_baselines(self, scenario_name: str, snapshot: dict) -> None:
        """Saves MFD analysis baselines ('last' always updated, 'first' set once if absent) in DB."""
        if not scenario_name or not snapshot:
            return
        conn = self.engine.get_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            serialized = json.dumps(snapshot)

            if self.engine.db_type == "postgres":
                query_last = """
                INSERT INTO mfd_analysis_cache (scenario_name, cache_type, metrics_cache, updated_at)
                VALUES (%s, 'last', %s, NOW())
                ON CONFLICT (scenario_name, cache_type)
                DO UPDATE SET metrics_cache = EXCLUDED.metrics_cache, updated_at = NOW();
                """
                cursor.execute(query_last, (scenario_name, serialized))

                query_first_check = (
                    "SELECT 1 FROM mfd_analysis_cache WHERE scenario_name = %s AND cache_type = 'first';"
                )
                cursor.execute(query_first_check, (scenario_name,))
                if not cursor.fetchone():
                    query_first_ins = """
                    INSERT INTO mfd_analysis_cache (scenario_name, cache_type, metrics_cache, updated_at)
                    VALUES (%s, 'first', %s, NOW());
                    """
                    cursor.execute(query_first_ins, (scenario_name, serialized))
            else:
                query_last = """
                INSERT INTO mfd_analysis_cache (scenario_name, cache_type, metrics_cache, updated_at)
                VALUES (?, 'last', ?, CURRENT_TIMESTAMP)
                ON CONFLICT (scenario_name, cache_type)
                DO UPDATE SET metrics_cache = excluded.metrics_cache, updated_at = CURRENT_TIMESTAMP;
                """
                cursor.execute(query_last, (scenario_name, serialized))

                query_first_check = "SELECT 1 FROM mfd_analysis_cache WHERE scenario_name = ? AND cache_type = 'first';"
                cursor.execute(query_first_check, (scenario_name,))
                if not cursor.fetchone():
                    query_first_ins = """
                    INSERT INTO mfd_analysis_cache (scenario_name, cache_type, metrics_cache, updated_at)
                    VALUES (?, 'first', ?, CURRENT_TIMESTAMP);
                    """
                    cursor.execute(query_first_ins, (scenario_name, serialized))

            conn.commit()
        except Exception as e:
            logging.error(f"[ANALYSIS_CACHE_REPO] Failed to save MFD analysis baselines for '{scenario_name}': {e}", exc_info=True)
        finally:
            if conn:
                conn.close()
