# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: src/repositories/step_decision_repo.py
# Author: Gabriel Moraes
# Date: August 2026

import datetime
import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import psycopg2
from psycopg2.extras import execute_values

if TYPE_CHECKING:
    from src.database.db_engine import DatabaseEngine
    from src.utils.locale_manager_backend import LocaleManagerBackend


class StepDecisionRepository:
    """
    High-performance repository for real-time step decision counters (codes 0-5),
    operational session lifecycle management, and SUMO topology dictionary storage.
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
        self.ensure_tables_exist()

    def ensure_tables_exist(self) -> bool:
        """Ensures that step_decision_counters, operation_sessions, and topology_dictionary tables exist."""
        conn = self.engine.get_connection()
        if not conn:
            return False
        try:
            with conn.cursor() as cursor:
                # 1. Step Decision Counters table (pure BIGINT numeric agent_id)
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

                # 2. Operational Sessions table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS operation_sessions (
                        session_id BIGSERIAL PRIMARY KEY,
                        start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        end_time TIMESTAMP,
                        status VARCHAR(50) DEFAULT 'EM_OPERACAO',
                        error_message TEXT
                    );
                """
                )

                # 3. Topology Dictionary table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS topology_dictionary (
                        id BIGSERIAL PRIMARY KEY,
                        element_type VARCHAR(20) NOT NULL,
                        raw_net_id VARCHAR(255) UNIQUE NOT NULL,
                        numeric_id BIGINT NOT NULL,
                        custom_name VARCHAR(255) NOT NULL,
                        from_node VARCHAR(100),
                        to_node VARCHAR(100),
                        is_bidirectional_pair BOOLEAN DEFAULT FALSE
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

    def start_session(self) -> Optional[int]:
        """Registers a new operational session start_time in PostgreSQL."""
        conn = self.engine.get_connection()
        if not conn:
            return None
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO operation_sessions (start_time, status)
                    VALUES (CURRENT_TIMESTAMP, 'EM_OPERACAO')
                    RETURNING session_id;
                """
                )
                sid = cursor.fetchone()[0]
            conn.commit()
            return sid
        except Exception as e:
            logging.error(f"[StepDecisionRepo] Error starting operation session: {e}")
            try:
                conn.rollback()
            except Exception:
                pass
            return None

    def end_session(self, session_id: int, status: str = "FINALIZADO_NORMAL", error_msg: Optional[str] = None) -> bool:
        """Updates operation session end_time and status in PostgreSQL."""
        conn = self.engine.get_connection()
        if not conn or not session_id:
            return False
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE operation_sessions
                    SET end_time = CURRENT_TIMESTAMP, status = %s, error_message = %s
                    WHERE session_id = %s;
                """,
                    (status, error_msg, session_id),
                )
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"[StepDecisionRepo] Error ending operation session {session_id}: {e}")
            try:
                conn.rollback()
            except Exception:
                pass
            return False

    def bulk_save_topology_elements(self, elements: List[Dict[str, Any]]) -> bool:
        """Saves or updates topology dictionary elements in PostgreSQL."""
        if not elements:
            return True
        conn = self.engine.get_connection()
        if not conn:
            return False

        batch = [
            (
                el["element_type"],
                el["raw_net_id"],
                int(el["numeric_id"]),
                el["custom_name"],
                el.get("from_node"),
                el.get("to_node"),
                bool(el.get("is_bidirectional_pair", False)),
            )
            for el in elements
        ]

        query = """
            INSERT INTO topology_dictionary (
                element_type, raw_net_id, numeric_id, custom_name, from_node, to_node, is_bidirectional_pair
            ) VALUES %s
            ON CONFLICT (raw_net_id) DO UPDATE SET
                numeric_id = EXCLUDED.numeric_id,
                from_node = EXCLUDED.from_node,
                to_node = EXCLUDED.to_node,
                is_bidirectional_pair = EXCLUDED.is_bidirectional_pair;
        """
        try:
            with conn.cursor() as cursor:
                execute_values(cursor, query, batch, page_size=500)
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"[StepDecisionRepo] Bulk save topology elements failed: {e}")
            try:
                conn.rollback()
            except Exception:
                pass
            return False

    def update_topology_custom_name(self, element_type: str, raw_net_id: str, new_name: str) -> bool:
        """Updates user configured custom name for a street or intersection in PostgreSQL."""
        conn = self.engine.get_connection()
        if not conn:
            return False
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE topology_dictionary
                    SET custom_name = %s
                    WHERE UPPER(element_type) = UPPER(%s) AND raw_net_id = %s;
                """,
                    (new_name, element_type, raw_net_id),
                )
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"[StepDecisionRepo] Failed to update custom name for {raw_net_id}: {e}")
            try:
                conn.rollback()
            except Exception:
                pass
            return False

    def get_topology_custom_name(self, element_type: str, raw_net_id: str) -> Optional[str]:
        """Queries custom user-configured name for a street or intersection from PostgreSQL."""
        conn = self.engine.get_connection()
        if not conn:
            return None
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT custom_name FROM topology_dictionary
                    WHERE UPPER(element_type) = UPPER(%s) AND (raw_net_id = %s OR numeric_id = %s);
                """,
                    (element_type, raw_net_id, self._to_int_id(raw_net_id)),
                )
                row = cursor.fetchone()
                return str(row[0]) if row and row[0] else None
        except Exception:
            return None

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

                # Fetch top veto reason code
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
        if isinstance(val, int):
            return val
        s = str(val or "")
        digits = "".join([c for c in s if c.isdigit()])
        if digits:
            return int(digits)
        return abs(hash(s)) % (10**10)
