# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Step Decision Analytics (Query / CQRS / Clean Architecture / SOLID: SRP).
Encapsulates analytics queries and compliance rate computations for XAI reporting.
"""

import logging
from typing import Any, Dict, List, Optional

from src.database.connection_pool import db_transaction
from src.repositories.topology_dictionary_repo import TopologyDictionaryRepository


class StepDecisionAnalytics:
    """Provides analytical aggregation queries for agent decisions and veto statistics."""

    @staticmethod
    def _to_int_id(val: Any) -> int:
        """Extracts integer numeric digits from agent_id string/int."""
        return TopologyDictionaryRepository._to_int_id(val)

    @classmethod
    def get_all_audited_agent_ids(cls, engine: Any) -> List[str]:
        """Queries database to get all unique agent_ids recorded in step_decision_counters."""
        try:
            with db_transaction(engine, commit=False) as (conn, cursor):
                if not conn or not cursor:
                    return []
                cursor.execute("SELECT DISTINCT agent_id FROM step_decision_counters ORDER BY agent_id;")
                rows = cursor.fetchall()
                return [str(r[0]) for r in rows if r and r[0] is not None]
        except Exception as e:
            logging.warning(f"[StepDecisionAnalytics] Failed to fetch audited agent_ids: {e}", exc_info=True)
            return []

    @classmethod
    def get_guardian_veto_statistics(
        cls,
        engine: Any,
        veto_reason_text: Dict[int, str],
        agent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fetches decision audit statistics for XAI reports from step_decision_counters DB table."""
        default_stats = {
            "total_evaluated": 0,
            "total_approved": 0,
            "temporal_interventions": 0,
            "critical_vetoes": 0,
            "exploratory_vetoes": 0,
            "compliance_rate": 100.0,
            "top_veto_reason": veto_reason_text[0],
        }
        num_agent_id = cls._to_int_id(agent_id) if agent_id else None

        try:
            with db_transaction(engine, commit=False) as (conn, cursor):
                if not conn or not cursor:
                    return default_stats
                if num_agent_id is not None:
                    cursor.execute(
                        """
                        SELECT
                            COALESCE(SUM(count), 0) AS total_eval,
                            COALESCE(SUM(CASE WHEN decision_code = 0 THEN count ELSE 0 END), 0) AS approved,
                            COALESCE(SUM(CASE WHEN decision_code IN (1, 2, 3, 4) THEN count ELSE 0 END), 0) AS temporal_cnt,
                            COALESCE(SUM(CASE WHEN decision_code = 5 THEN count ELSE 0 END), 0) AS critical_cnt,
                            COALESCE(SUM(CASE WHEN decision_code = 7 THEN count ELSE 0 END), 0) AS exploratory_cnt
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
                            COALESCE(SUM(CASE WHEN decision_code = 5 THEN count ELSE 0 END), 0) AS critical_cnt,
                            COALESCE(SUM(CASE WHEN decision_code = 7 THEN count ELSE 0 END), 0) AS exploratory_cnt
                        FROM step_decision_counters;
                        """
                    )

                row = cursor.fetchone()
                total_eval = int(row[0]) if row and row[0] else 0
                approved = int(row[1]) if row and row[1] else 0
                temporal_cnt = int(row[2]) if row and row[2] else 0
                critical_cnt = int(row[3]) if row and row[3] else 0
                exploratory_cnt = int(row[4]) if row and len(row) > 4 and row[4] else 0

                if total_eval == 0:
                    return {
                        **default_stats,
                        "top_veto_reason": "Aguardando Amostragem em Tempo Real",
                    }

                rate = (approved / total_eval) * 100.0

                if temporal_cnt == 0 and critical_cnt == 0 and exploratory_cnt == 0:
                    top_reason = veto_reason_text[0]
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
                    top_reason = veto_reason_text.get(reason_code, veto_reason_text[1])

                return {
                    "total_evaluated": total_eval,
                    "total_approved": approved,
                    "temporal_interventions": temporal_cnt,
                    "critical_vetoes": critical_cnt,
                    "exploratory_vetoes": exploratory_cnt,
                    "compliance_rate": round(rate, 1),
                    "top_veto_reason": top_reason,
                }
        except Exception as e:
            logging.warning(f"[StepDecisionAnalytics] Failed to query statistics: {e}", exc_info=True)
            return {
                **default_stats,
                "top_veto_reason": "Aguardando Amostragem em Tempo Real",
            }
