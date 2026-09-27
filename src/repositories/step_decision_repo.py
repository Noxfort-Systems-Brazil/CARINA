# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: src/repositories/step_decision_repo.py
# Author: Gabriel Moraes
# Date: September 2026

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from psycopg2.extras import execute_values

from src.repositories.operation_session_repo import OperationSessionRepository
from src.repositories.topology_dictionary_repo import TopologyDictionaryRepository

if TYPE_CHECKING:
    from src.database.db_engine import DatabaseEngine
    from src.utils.locale_manager_backend import LocaleManagerBackend


class StepDecisionRepository:
    """
    High-performance repository for real-time step decision counters (codes 0-5),
    operational session lifecycle management, and SUMO topology dictionary storage.
    Follows Clean Architecture Facade Pattern to ensure 100% backward compatibility.
    """

    # Enums for 0-5 Decision / Veto Codes
    DECISION_CODES = {
        "APPROVED": 0,
        "PASS": 0,
        "MIN_GREEN": 1,
        "MIN_YELLOW": 2,
        "MIN_ALL_RED": 3,
        "MIN_RED": 4,
        "SPILLBACK_D3QN": 5,
    }

    # Reverse Mappings for ABNT Report Formatting
    VETO_REASON_TEXT = {
        0: "Nenhum (Decisão Aprovada)",
        1: "Proteção de Tempo Mínimo de Verde (Min Green = 10s)",
        2: "Proteção de Tempo Mínimo de Amarelo (Yellow Clearance)",
        3: "Proteção de Tempo Mínimo de Vermelho Integral (All-Red)",
        4: "Proteção de Tempo Mínimo de Vermelho Geral (Min Red)",
        5: "Veto Crítico de Spillback (Redes Neurais D3QN)",
    }

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
            logging.error(f"[StepDecisionRepo] Error ensuring tables exist: {e}")
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

        query = """
            INSERT INTO step_decision_counters (agent_id, decision_code, count)
            VALUES %s
            ON CONFLICT (agent_id, decision_code)
            DO UPDATE SET count = step_decision_counters.count + EXCLUDED.count;
        """
        try:
            with conn.cursor() as cursor:
                execute_values(cursor, query, batch_tuples, page_size=1000)
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"[StepDecisionRepo] Counter batch update failed: {e}")
            try:
                conn.rollback()
            except Exception:
                pass
            return False

    # --- Delegated Operation Session Methods (SRP) ---
    def start_session(self) -> Optional[int]:
        """Registers a new operational session start_time in PostgreSQL."""
        return self.session_repo.start_session()

    def end_session(self, session_id: int, status: str = "FINALIZADO_NORMAL", error_msg: Optional[str] = None) -> bool:
        """Updates operation session end_time and status in PostgreSQL."""
        return self.session_repo.end_session(session_id, status, error_msg)

    # --- Delegated Topology Dictionary Methods (SRP) ---
    def bulk_save_topology_elements(self, elements: List[Dict[str, Any]]) -> bool:
        """Saves or updates topology dictionary elements in PostgreSQL."""
        return self.topology_repo.bulk_save_topology_elements(elements)

    def update_topology_custom_name(self, element_type: str, raw_net_id: str, new_name: str) -> bool:
        """Updates user configured custom name for a street or intersection in PostgreSQL."""
        return self.topology_repo.update_topology_custom_name(element_type, raw_net_id, new_name)

    def get_topology_custom_name(self, element_type: str, raw_net_id: str) -> Optional[str]:
        """Queries custom user-configured name for a street or intersection from PostgreSQL."""
        return self.topology_repo.get_topology_custom_name(element_type, raw_net_id)

    # --- Decision Veto Statistics & Analytics ---
    def get_all_audited_agent_ids(self) -> List[str]:
        """Queries PostgreSQL to get all unique agent_ids (BIGINT) recorded in step_decision_counters."""
        conn = self.engine.get_connection()
        if not conn:
            return []
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT DISTINCT agent_id FROM step_decision_counters ORDER BY agent_id;")
                rows = cursor.fetchall()
                return [str(r[0]) for r in rows if r and r[0] is not None]
        except Exception as e:
            logging.warning(f"[StepDecisionRepo] Failed to fetch audited agent_ids: {e}")
            return []

    def get_guardian_veto_statistics(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Fetches decision audit statistics for XAI reports from step_decision_counters DB table."""
        conn = self.engine.get_connection()
        if not conn:
            return {
                "total_evaluated": 0,
                "total_approved": 0,
                "temporal_interventions": 0,
                "critical_vetoes": 0,
                "compliance_rate": 100.0,
                "top_veto_reason": self.VETO_REASON_TEXT[0],
            }

        num_agent_id = self._to_int_id(agent_id) if agent_id else None

        try:
            with conn.cursor() as cursor:
                if num_agent_id is not None:
                    cursor.execute(
                        """
                        SELECT
                            COALESCE(SUM(count), 0) AS total_eval,
                            COALESCE(SUM(CASE WHEN decision_code = 0 THEN count ELSE 0 END), 0) AS approved,
                            COALESCE(SUM(CASE WHEN decision_code IN (1, 2, 3, 4) THEN count ELSE 0 END), 0) AS temporal_cnt,
                            COALESCE(SUM(CASE WHEN decision_code = 5 THEN count ELSE 0 END), 0) AS critical_cnt
                        FROM step_decision_counters
                        WHERE agent_id = %s;
                        """,
                        (num_agent_id,),
                    )
                else:
                    cursor.execute(
                        """
                        SELECT
                            COALESCE(SUM(count), 0) AS total_eval,
                            COALESCE(SUM(CASE WHEN decision_code = 0 THEN count ELSE 0 END), 0) AS approved,
                            COALESCE(SUM(CASE WHEN decision_code IN (1, 2, 3, 4) THEN count ELSE 0 END), 0) AS temporal_cnt,
                            COALESCE(SUM(CASE WHEN decision_code = 5 THEN count ELSE 0 END), 0) AS critical_cnt
                        FROM step_decision_counters;
                        """
                    )

                row = cursor.fetchone()
                total_eval = int(row[0]) if row and row[0] else 0
                approved = int(row[1]) if row and row[1] else 0
                temporal_cnt = int(row[2]) if row and row[2] else 0
                critical_cnt = int(row[3]) if row and row[3] else 0

                if total_eval == 0:
                    return {
                        "total_evaluated": 0,
                        "total_approved": 0,
                        "temporal_interventions": 0,
                        "critical_vetoes": 0,
                        "compliance_rate": 100.0,
                        "top_veto_reason": "Aguardando Amostragem em Tempo Real",
                    }

                rate = (approved / total_eval) * 100.0

                if temporal_cnt == 0 and critical_cnt == 0:
                    top_reason = self.VETO_REASON_TEXT[0]
                else:
                    if num_agent_id is not None:
                        cursor.execute(
                            """
                            SELECT decision_code, SUM(count) AS cnt
                            FROM step_decision_counters
                            WHERE decision_code > 0 AND agent_id = %s
                            GROUP BY decision_code
                            ORDER BY cnt DESC LIMIT 1;
                            """,
                            (num_agent_id,),
                        )
                    else:
                        cursor.execute(
                            """
                            SELECT decision_code, SUM(count) AS cnt
                            FROM step_decision_counters
                            WHERE decision_code > 0
                            GROUP BY decision_code
                            ORDER BY cnt DESC LIMIT 1;
                            """
                        )
                    vrow = cursor.fetchone()
                    reason_code = int(vrow[0]) if vrow else 1
                    top_reason = self.VETO_REASON_TEXT.get(reason_code, self.VETO_REASON_TEXT[1])

                return {
                    "total_evaluated": total_eval,
                    "total_approved": approved,
                    "temporal_interventions": temporal_cnt,
                    "critical_vetoes": critical_cnt,
                    "compliance_rate": round(rate, 1),
                    "top_veto_reason": top_reason,
                }
        except Exception as e:
            logging.warning(f"[StepDecisionRepo] Failed to query statistics: {e}")
            return {
                "total_evaluated": 0,
                "total_approved": 0,
                "temporal_interventions": 0,
                "critical_vetoes": 0,
                "compliance_rate": 100.0,
                "top_veto_reason": "Aguardando Amostragem em Tempo Real",
            }

    @staticmethod
    def _to_int_id(val: Any) -> int:
        """Extracts integer numeric digits from agent_id string/int."""
        return TopologyDictionaryRepository._to_int_id(val)
