# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Specialist Repository for Denied/Unauthorized Vehicles (SRP / Clean Architecture).
Strictly responsible for persisting the auto-registration blocklist (evp_denied_fleet).
"""

import logging
from typing import Any, Callable, List, Optional

from src.evp.evp_db_executor import EVPDatabaseExecutor

logger = logging.getLogger(__name__)


class EVPDeniedRepository:
    """Manages the denylist of removed vehicles to prevent auto-registration."""

    def __init__(self, engine: Any, close_conn_fn: Optional[Callable[[Any], None]] = None):
        self.executor = EVPDatabaseExecutor(engine, close_conn_fn)
        self.ensure_table_exists()

    @property
    def engine(self) -> Any:
        return self.executor.engine

    def ensure_table_exists(self) -> None:
        """Ensures the evp_denied_fleet table exists."""
        try:
            with self.executor.transaction() as cursor:
                if cursor is None:
                    return
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS evp_denied_fleet (
                        vehicle_id VARCHAR(64) PRIMARY KEY,
                        denied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    """
                )
        except Exception as e:
            logger.warning(f"[EVPDeniedRepository] Aviso ao verificar/criar tabela evp_denied_fleet: {e}", exc_info=True)

    def add_denied_vehicle(self, vehicle_id: str) -> bool:
        """Adds vehicle to the unauthorized/removed list to prevent auto-registration."""
        try:
            with self.executor.transaction() as cursor:
                if cursor is None:
                    return False
                if self.executor.is_postgres:
                    cursor.execute(
                        """
                        INSERT INTO evp_denied_fleet (vehicle_id)
                        VALUES (%s)
                        ON CONFLICT (vehicle_id) DO NOTHING;
                        """,
                        (vehicle_id,),
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO evp_denied_fleet (vehicle_id)
                        VALUES (?)
                        ON CONFLICT(vehicle_id) DO NOTHING;
                        """,
                        (vehicle_id,),
                    )
                return True
        except Exception as e:
            logger.error(f"[EVPDeniedRepository] Erro ao registrar viatura negada {vehicle_id}: {e}", exc_info=True)
            return False

    def remove_denied_vehicle(self, vehicle_id: str) -> bool:
        """Removes vehicle from denylist (in case it is re-registered manually by the operator)."""
        try:
            with self.executor.transaction() as cursor:
                if cursor is None:
                    return False
                if self.executor.is_postgres:
                    cursor.execute(
                        "DELETE FROM evp_denied_fleet WHERE vehicle_id = %s;",
                        (vehicle_id,),
                    )
                else:
                    cursor.execute(
                        "DELETE FROM evp_denied_fleet WHERE vehicle_id = ?;",
                        (vehicle_id,),
                    )
                return True
        except Exception as e:
            logger.error(f"[EVPDeniedRepository] Erro ao remover viatura de negadas {vehicle_id}: {e}", exc_info=True)
            return False

    def get_denied_vehicles(self) -> List[str]:
        """Retrieves list of vehicle IDs explicitly unauthorized/removed."""
        try:
            with self.executor.transaction() as cursor:
                if cursor is None:
                    return []
                cursor.execute("SELECT vehicle_id FROM evp_denied_fleet;")
                rows = cursor.fetchall()
                return [row[0] for row in rows]
        except Exception as e:
            logger.error(f"[EVPDeniedRepository] Erro ao listar viaturas negadas: {e}", exc_info=True)
            return []

    def clear_denied_fleet(self) -> bool:
        """Clears all records of denied vehicles."""
        try:
            with self.executor.transaction() as cursor:
                if cursor is None:
                    return False
                cursor.execute("DELETE FROM evp_denied_fleet;")
                return True
        except Exception as e:
            logger.error(f"[EVPDeniedRepository] Erro ao limpar viaturas negadas: {e}", exc_info=True)
            return False
