# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import Any, Dict, List, Optional

from utils.locale_manager_backend import LocaleManagerBackend

_UNSET = object()


class ReportDataCollector:
    """
    Collects and extracts persistence data (e.g. Guardian D3QN statistics, step decisions)
    required for XAI report rendering, decoupling database access from presentation builders.
    """

    def __init__(self, locale_manager: Optional[LocaleManagerBackend] = None, step_repo: Any = _UNSET) -> None:
        self.locale_manager = locale_manager if locale_manager is not None else LocaleManagerBackend()
        self._step_repo = step_repo

    def _resolve_step_repo(self, explicit_repo: Any = _UNSET) -> Optional[Any]:
        """Resolves step decision repository instance."""
        if explicit_repo is not _UNSET:
            return explicit_repo
        if self._step_repo is not _UNSET:
            return self._step_repo

        try:
            from database.database_manager import DatabaseManager

            db_mgr = DatabaseManager(self.locale_manager)
            return getattr(db_mgr, "step_decision_repo", None)
        except Exception as e:
            logging.debug(f"[ReportDataCollector] DatabaseManager initialization bypassed: {e}")
            return None

    def collect_guardian_statistics(
        self, agent_ids: List[str], default_reason_text: str = "Aguardando Amostragem", step_repo: Any = _UNSET
    ) -> Dict[str, Dict[str, Any]]:
        """
        Fetches and normalizes Guardian veto and compliance statistics for all audited agents.
        """
        repo = self._resolve_step_repo(step_repo)
        stats_by_agent: Dict[str, Dict[str, Any]] = {}

        for aid in agent_ids:
            if repo:
                try:
                    stats = repo.get_guardian_veto_statistics(aid)
                    eval_count = stats["total_evaluated"]
                    approved_count = stats["total_approved"]
                    temporal_count = stats.get("temporal_interventions", 0)
                    critical_count = stats.get("critical_vetoes", 0)
                    compliance_rate = stats.get("compliance_rate", 100.0)
                    rate_str = f"{compliance_rate:.1f}%".replace(".", ",")
                    approved_pct = f"{compliance_rate:.1f}".replace(".", ",")
                    reason = stats.get("top_veto_reason", default_reason_text)
                except Exception as e:
                    logging.debug(f"[ReportDataCollector] Failed to query guardian stats for agent {aid}: {e}")
                    eval_count, approved_count, temporal_count, critical_count = 0, 0, 0, 0
                    compliance_rate = 100.0
                    rate_str = "100,0%"
                    approved_pct = "100,0"
                    reason = default_reason_text
            else:
                eval_count, approved_count, temporal_count, critical_count = 0, 0, 0, 0
                compliance_rate = 100.0
                rate_str = "100,0%"
                approved_pct = "100,0"
                reason = default_reason_text

            stats_by_agent[aid] = {
                "eval_count": eval_count,
                "approved_count": approved_count,
                "temporal_count": temporal_count,
                "critical_count": critical_count,
                "compliance_rate": compliance_rate,
                "rate_str": rate_str,
                "approved_pct": approved_pct,
                "reason": reason,
            }

        return stats_by_agent
