# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import Any, Optional


class SimulationRunResolver:
    """Encapsulates resolving or creating simulation run IDs in the database."""

    @classmethod
    def resolve_run_id(cls, db_manager: Optional[Any], scenario_name: str) -> int:
        """
        Attempts to query the latest run ID for the scenario from the database
        or creates a new run entry if not present.
        """
        if not db_manager:
            return 1

        try:
            conn = db_manager.engine.get_connection()
            if conn:
                cursor = conn.cursor()
                ph = "?" if getattr(db_manager.engine, "db_type", None) != "postgres" else "%s"
                cursor.execute(
                    f"SELECT run_id FROM simulation_runs WHERE scenario_name = {ph} ORDER BY run_id DESC LIMIT 1;",
                    (scenario_name,),
                )
                row = cursor.fetchone()
                if row:
                    run_id = row[0]
                else:
                    run_id = db_manager.create_simulation_run(scenario_name)
                conn.close()
                return run_id
        except Exception as e:
            logging.error(f"[SimulationRunResolver] Error getting or creating run_id: {e}", exc_info=True)

        return 1
