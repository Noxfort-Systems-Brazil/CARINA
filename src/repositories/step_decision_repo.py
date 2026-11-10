# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

try:
    from psycopg2.extras import execute_values
except ImportError:
    execute_values = None

from src.domain.veto_reasons import (
    DECISION_CODES as DOMAIN_DECISION_CODES,
    VETO_REASON_TEXT as DOMAIN_VETO_REASON_TEXT,
)
from src.repositories.operation_session_repo import OperationSessionRepository
from src.repositories.step_decision_analytics import StepDecisionAnalytics
from src.repositories.topology_dictionary_repo import TopologyDictionaryRepository

if TYPE_CHECKING:
    from src.database.db_engine import DatabaseEngine
    from src.utils.locale_manager_backend import LocaleManagerBackend


class StepDecisionRepository:
    """
    High-performance repository for real-time step decision counters (codes 0-5),
    operational session lifecycle management, and SUMO topology dictionary storage.
    Delegates analytics queries to StepDecisionAnalytics (CQRS / SRP).
    """

    DECISION_CODES = DOMAIN_DECISION_CODES
    VETO_REASON_TEXT = DOMAIN_VETO_REASON_TEXT

    def __init__(self, engine: "DatabaseEngine", locale_manager: "LocaleManagerBackend"):
        self.engine = engine
        self.locale_manager = locale_manager

        # Specialized sub-repositories (Clean Architecture / SRP)
        self.session_repo = OperationSessionRepository(engine)
        self.topology_repo = TopologyDictionaryRepository(engine)

        self.ensure_tables_exist()

    def ensure_tables_exist(self) -> bool:
        """Ensures that step_decision_counters table exists, alongside delegated tables."""
        conn = self.engine.get_connection()
        if not conn:
            return False
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS step_decision_counters (
                        agent_id BIGINT NOT NULL,
                        decision_code INTEGER NOT NULL,
                        count BIGINT NOT NULL DEFAULT 0,
                        PRIMARY KEY (agent_id, decision_code)
                    );
                    """
                )
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"[StepDecisionRepo] Error ensuring tables exist: {e}", exc_info=True)
            try:
                conn.rollback()
            except Exception:
                pass
            return False

    def increment_decision_counter_batch(self, batch_tuples: List[Tuple[int, int, int]]) -> bool:
        """
        Executes high-speed atomic UPSERT batch updates into step_decision_counters.
        batch_tuples: [(agent_id_bigint, decision_code_int, count_bigint)]
        """
        if not batch_tuples:
            return True

        conn = self.engine.get_connection()
        if not conn:
            return False

        try:
            with conn.cursor() as cursor:
                if getattr(self.engine, "db_type", "sqlite") == "postgres":
                    from psycopg2.extras import execute_values

                    query_pg = """
                        INSERT INTO step_decision_counters (agent_id, decision_code, count)
                        VALUES %s
                        ON CONFLICT (agent_id, decision_code)
                        DO UPDATE SET count = step_decision_counters.count + EXCLUDED.count;
                    """
                    execute_values(cursor, query_pg, batch_tuples, page_size=1000)
                else:
                    query_sqlite = """
                        INSERT INTO step_decision_counters (agent_id, decision_code, count)
                        VALUES (?, ?, ?)
                        ON CONFLICT (agent_id, decision_code)
                        DO UPDATE SET count = step_decision_counters.count + excluded.count;
                    """
                    cursor.executemany(query_sqlite, batch_tuples)
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"[StepDecisionRepo] Counter batch update failed: {e}", exc_info=True)
            try:
                conn.rollback()
            except Exception:
                pass
            return False

    # --- Delegated Operation Session Methods (SRP) ---
    def start_session(self) -> Optional[int]:
        return self.session_repo.start_session()

    def end_session(self, session_id: int, status: str = "FINALIZADO_NORMAL", error_msg: Optional[str] = None) -> bool:
        return self.session_repo.end_session(session_id, status, error_msg)

    # --- Delegated Topology Dictionary Methods (SRP) ---
    def bulk_save_topology_elements(self, elements: List[Dict[str, Any]]) -> bool:
        return self.topology_repo.bulk_save_topology_elements(elements)

    def update_topology_custom_name(self, element_type: str, raw_net_id: str, new_name: str) -> bool:
        return self.topology_repo.update_topology_custom_name(element_type, raw_net_id, new_name)

    def get_topology_custom_name(self, element_type: str, raw_net_id: str) -> Optional[str]:
        return self.topology_repo.get_topology_custom_name(element_type, raw_net_id)

    # --- Delegated Decision Veto Statistics & Analytics (CQRS / SRP) ---
    def get_all_audited_agent_ids(self) -> List[str]:
        return StepDecisionAnalytics.get_all_audited_agent_ids(self.engine)

    def get_guardian_veto_statistics(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        return StepDecisionAnalytics.get_guardian_veto_statistics(
            self.engine, self.VETO_REASON_TEXT, agent_id
        )

    @staticmethod
    def _to_int_id(val: Any) -> int:
        return StepDecisionAnalytics._to_int_id(val)
