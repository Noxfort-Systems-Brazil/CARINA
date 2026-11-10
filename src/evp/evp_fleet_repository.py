# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Specialist Repository for Authorized Emergency Fleet (EVP).
Responsible for persisting and synchronizing authorized vehicle records.
Delegates SQL query definitions to EVPFleetSql (Infrastructure / SRP).
"""

import logging
from typing import Any, Callable, List, Optional

from src.evp.evp_db_executor import EVPDatabaseExecutor
from src.evp.evp_denied_repository import EVPDeniedRepository
from src.evp.evp_models import CorporationType, RegisteredVehicle
from src.evp.infrastructure.evp_fleet_sql import EVPFleetSql

logger = logging.getLogger(__name__)


class EVPFleetRepository:
    """Manages persistence of registered vehicles for the municipal emergency fleet."""

    def __init__(self, engine: Any, close_conn_fn: Optional[Callable[[Any], None]] = None):
        self.engine = engine
        self._close_conn = close_conn_fn
        self.executor = EVPDatabaseExecutor(engine, close_conn_fn)
        self.denied_repo = EVPDeniedRepository(engine, close_conn_fn)
        self.ensure_table_exists()

    def ensure_table_exists(self) -> None:
        """Ensures the fleet and denied vehicle tables exist."""
        try:
            with self.executor.transaction() as cursor:
                if cursor is not None:
                    cursor.execute(EVPFleetSql.CREATE_REGISTERED_FLEET_TABLE)
        except Exception as e:
            logger.warning(f"[EVPFleetRepository] Aviso ao verificar/criar tabela de frota: {e}", exc_info=True)

        self.denied_repo.ensure_table_exists()

    def _build_vehicle_params(self, vehicle: RegisteredVehicle, is_pg: bool) -> tuple:
        return (
            vehicle.vehicle_id,
            vehicle.corporation.value,
            vehicle.plate,
            vehicle.description,
            vehicle.device_id,
            vehicle.ip_address,
            vehicle.port,
            vehicle.protocol,
            vehicle.auth_token,
            vehicle.is_active if is_pg else (1 if vehicle.is_active else 0),
        )

    def save_registered_vehicle(self, vehicle: RegisteredVehicle) -> bool:
        """Saves or updates formal vehicle registration in PostgreSQL/SQLite database."""
        try:
            with self.executor.transaction() as cursor:
                if cursor is None:
                    return False
                is_pg = self.executor.is_postgres
                sql = EVPFleetSql.get_upsert_vehicle_query(is_pg)
                cursor.execute(sql, self._build_vehicle_params(vehicle, is_pg))
                logger.info(f"[EVPFleetRepository] Viatura {vehicle.vehicle_id} persistida no banco com sucesso.")
                return True
        except Exception as e:
            logger.error(f"[EVPFleetRepository] Erro ao salvar viatura cadastrada {vehicle.vehicle_id}: {e}", exc_info=True)
            return False

    def save_registered_vehicles_batch(self, vehicles: List[RegisteredVehicle]) -> int:
        """Saves or updates a list of vehicles in batch in the database."""
        if not vehicles:
            return 0
        is_pg = self.executor.is_postgres
        sql = EVPFleetSql.get_upsert_vehicle_query(is_pg)
        saved_count = 0
        try:
            with self.executor.transaction() as cursor:
                if cursor is None:
                    return 0
                for v in vehicles:
                    cursor.execute(sql, self._build_vehicle_params(v, is_pg))
                    saved_count += 1
                logger.info(f"[EVPFleetRepository] {saved_count} viaturas persistidas em lote no banco.")
                return saved_count
        except Exception as e:
            logger.error(f"[EVPFleetRepository] Erro ao salvar lote de viaturas: {e}", exc_info=True)
            return saved_count

    def delete_registered_vehicle(self, vehicle_id: str) -> bool:
        """Removes formal vehicle registration from the database."""
        try:
            with self.executor.transaction() as cursor:
                if cursor is None:
                    return False
                sql = EVPFleetSql.get_delete_registered_query(self.executor.is_postgres)
                cursor.execute(sql, (vehicle_id,))
                deleted = bool(cursor.rowcount and cursor.rowcount > 0)
                logger.info(f"[EVPFleetRepository] Viatura {vehicle_id} deletada do banco.")
                return deleted
        except Exception as e:
            logger.error(f"[EVPFleetRepository] Erro ao deletar viatura {vehicle_id}: {e}", exc_info=True)
            return False

    def get_registered_vehicles(self) -> List[RegisteredVehicle]:
        """Loads all registered vehicles from the database."""
        vehicles: List[RegisteredVehicle] = []
        try:
            with self.executor.transaction() as cursor:
                if cursor is None:
                    return []
                cursor.execute(EVPFleetSql.SELECT_ALL_REGISTERED)
                rows = cursor.fetchall()
                for row in rows:
                    vehicles.append(
                        RegisteredVehicle(
                            vehicle_id=row[0],
                            corporation=CorporationType.from_string(row[1]),
                            plate=row[2] or "",
                            description=row[3] or "",
                            device_id=row[4] or "",
                            ip_address=row[5] or "",
                            port=int(row[6]) if row[6] is not None else 8085,
                            protocol=row[7] or "HTTP",
                            auth_token=row[8] or "",
                            is_active=bool(row[9]),
                        )
                    )
                return vehicles
        except Exception as e:
            logger.error(f"[EVPFleetRepository] Erro ao buscar frota cadastrada: {e}", exc_info=True)
            return vehicles

    # --- Delegated methods for EVPDeniedRepository (Backward compatibility) ---
    def add_denied_vehicle(self, vehicle_id: str) -> bool:
        return self.denied_repo.add_denied_vehicle(vehicle_id)

    def remove_denied_vehicle(self, vehicle_id: str) -> bool:
        return self.denied_repo.remove_denied_vehicle(vehicle_id)

    def get_denied_vehicles(self) -> List[str]:
        return self.denied_repo.get_denied_vehicles()

    def clear_all_fleet_db(self) -> bool:
        """Removes all fleet and denied vehicle records from the database."""
        try:
            with self.executor.transaction() as cursor:
                if cursor is None:
                    return False
                cursor.execute(EVPFleetSql.CLEAR_ALL_REGISTERED)
                self.denied_repo.clear_denied_fleet()
                logger.info("[EVPFleetRepository] Todas as viaturas cadastradas e negadas foram limpas do banco.")
                return True
        except Exception as e:
            logger.error(f"[EVPFleetRepository] Erro ao limpar frota do banco: {e}", exc_info=True)
            return False
