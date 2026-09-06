# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# File: src/xai/report_data_collector.py
# Author: Gabriel Moraes
# Date: August 14, 2026

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
