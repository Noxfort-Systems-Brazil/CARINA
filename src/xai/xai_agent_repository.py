# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import glob
import logging
import os
from typing import List, Optional

from utils.locale_manager_backend import LocaleManagerBackend


class XaiAgentRepository:
    """
    Repository responsible for discovering and resolving audited traffic controller (Agent) IDs
    across filesystem checkpoints and PostgreSQL step decision logs.
    """

    def __init__(self, scenario_results_dir: str, locale_manager: Optional[LocaleManagerBackend] = None) -> None:
        self.scenario_results_dir = scenario_results_dir
        self.locale_manager = locale_manager if locale_manager is not None else LocaleManagerBackend()
        self.checkpoints_dir = os.path.join(scenario_results_dir, "checkpoints")

    def discover_audited_agent_ids(self, primary_agent_id: Optional[str] = None) -> List[str]:
        """
        Discovers all available agent IDs from database records and saved checkpoints.
        Filters out reservation keywords like 'ALL', 'ALL_AGENTS', or 'TODOS'.
        """
        db_agent_ids: List[str] = []
        try:
            from database.database_manager import DatabaseManager

            db_mgr = DatabaseManager(self.locale_manager)
            step_repo = getattr(db_mgr, "step_decision_repo", None)
            if step_repo:
                db_agent_ids = step_repo.get_all_audited_agent_ids()
        except Exception as e:
            logging.debug(f"[XaiAgentRepository] Database query skipped or failed: {e}")

        checkpoint_files: List[str] = []
        if os.path.exists(self.checkpoints_dir):
            checkpoint_files = glob.glob(os.path.join(self.checkpoints_dir, "agent_*.pth"))

        agent_ids = list(db_agent_ids)
        for cf in checkpoint_files:
            base = os.path.basename(cf)
            aid = base.replace("agent_", "").replace(".pth", "")
            agent_ids.append(aid)

        if primary_agent_id and primary_agent_id.upper() not in ["ALL", "ALL_AGENTS", "TODOS"]:
            agent_ids.append(primary_agent_id)

        reserved_keywords = {"ALL", "ALL_AGENTS", "TODOS"}
        filtered_ids = sorted(list(set([aid for aid in agent_ids if aid and aid.upper() not in reserved_keywords])))
        return filtered_ids
