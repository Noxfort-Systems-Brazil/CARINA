# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Persistence Repository for the EVP Module.
Acts as a unified facade integrating forensic telemetry and fleet registration.
"""

import logging
from typing import Any, List, Optional

from src.evp.evp_fleet_repository import EVPFleetRepository
from src.evp.evp_models import EmergencyVehicle, RegisteredVehicle
from src.evp.evp_telemetry_repository import EVPTelemetryRepository

logger = logging.getLogger(__name__)


class EVPRepository:
    """
    Repository and facade for emergency telemetry persistence, fleet registration,
    and preemption auditing. Delegates operations to specialized repositories for each DDD aggregate.
    """

    def __init__(self, engine: Any = None):
        if engine is None:
            try:
                from src.database.db_engine import DatabaseEngine

                self.engine = DatabaseEngine(locale_manager=None)
            except Exception as e:
                logger.warning(f"[EVPRepository] Não foi possível inicializar DatabaseEngine padrão: {e}", exc_info=True)
                self.engine = None
        else:
            self.engine = engine

        self._telemetry_repo = EVPTelemetryRepository(self.engine, self._close_conn)
        self._fleet_repo = EVPFleetRepository(self.engine, self._close_conn)

    def _close_conn(self, conn: Any) -> None:
        """Ensures safe release or closure of connection."""
        if not conn:
            return
        if hasattr(self.engine, "release_connection"):
            self.engine.release_connection(conn)
        elif hasattr(conn, "close"):
            try:
                conn.close()
            except Exception as _exc:
                logger.debug("[evp] Ignored recoverable error: %s", _exc)

    def _ensure_tables_exist(self) -> None:
        """Ensures evp_telemetry_records and evp_registered_fleet tables exist."""
        if hasattr(self, "_telemetry_repo"):
            self._telemetry_repo.ensure_table_exists()
        if hasattr(self, "_fleet_repo"):
            self._fleet_repo.ensure_table_exists()

    def save_telemetry(self, vehicle: EmergencyVehicle, evp_triggered: bool = False) -> bool:
        """Saves telemetry snapshot to the database for forensics and auditing."""
        return self._telemetry_repo.save_telemetry(vehicle, evp_triggered=evp_triggered)

    def save_registered_vehicle(self, vehicle: RegisteredVehicle) -> bool:
        """Saves or updates formal vehicle registration in the database."""
        return self._fleet_repo.save_registered_vehicle(vehicle)

    def save_registered_vehicles_batch(self, vehicles: List[RegisteredVehicle]) -> int:
        """Saves or updates a list of vehicles in batch in the database."""
        return self._fleet_repo.save_registered_vehicles_batch(vehicles)

    def delete_registered_vehicle(self, vehicle_id: str) -> bool:
        """Removes formal vehicle registration from the database."""
        return self._fleet_repo.delete_registered_vehicle(vehicle_id)

    def get_registered_vehicles(self) -> List[RegisteredVehicle]:
        """Loads all registered vehicles from the database."""
        return self._fleet_repo.get_registered_vehicles()

    def add_denied_vehicle(self, vehicle_id: str) -> bool:
        """Adds vehicle to unauthorized/denied list."""
        return self._fleet_repo.add_denied_vehicle(vehicle_id)

    def remove_denied_vehicle(self, vehicle_id: str) -> bool:
        """Removes vehicle from unauthorized/denied list."""
        return self._fleet_repo.remove_denied_vehicle(vehicle_id)

    def get_denied_vehicles(self) -> List[str]:
        """Loads list of unauthorized/denied vehicles."""
        return self._fleet_repo.get_denied_vehicles()

    def clear_all_fleet_db(self) -> bool:
        """Removes all fleet and denied vehicle records from the database."""
        return self._fleet_repo.clear_all_fleet_db()

