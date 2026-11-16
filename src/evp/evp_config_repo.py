# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Static repository class responsible for database persistence and CSV import/export
of Emergency Vehicle Preemption (EVP) authorized fleet configurations.
Delegates SQL statements to EVPFleetSql (Infrastructure / SRP).
"""

import logging
import os
import threading
from typing import Any, Dict, List, Optional

from src.database.connection_pool import db_transaction
from src.evp.evp_fleet_csv_service import EVPFleetCsvService
from src.evp.evp_models import CorporationType, RegisteredVehicle
from src.evp.infrastructure.evp_fleet_sql import EVPFleetSql
from src.evp.interfaces.i_evp_config_repo import IEVPConfigRepository

logger = logging.getLogger(__name__)


class EVPConfigRepository(IEVPConfigRepository):
    """
    Manages loading, saving, importing, and exporting of emergency vehicle fleet configurations.
    Implements IEVPConfigRepository for Dependency Inversion (DIP) and provides
    backward-compatible static API facades. Delegates CSV parsing to EVPFleetCsvService (SRP).
    """

    _engine_cache: Dict[str, Any] = {}
    _engine_cache_lock = threading.Lock()

    def __init__(self, engine=None, locale_manager=None):
        self.engine = engine
        self.locale_manager = locale_manager

    def save_vehicle(self, vehicle: RegisteredVehicle) -> bool:
        return self.save_vehicle_db(vehicle, locale_manager=self.locale_manager, engine=self.engine)

    def load_all_vehicles(self) -> Dict[str, RegisteredVehicle]:
        return self.load_all_vehicles_db(locale_manager=self.locale_manager, engine=self.engine)

    def load_denied_vehicles(self) -> List[str]:
        return self.load_denied_vehicles_db(locale_manager=self.locale_manager, engine=self.engine)

    def remove_vehicle(self, vehicle_id: str) -> bool:
        return self.remove_vehicle_db(vehicle_id, locale_manager=self.locale_manager, engine=self.engine)

    def clear_all_vehicles(self) -> bool:
        return self.clear_all_vehicles_db(locale_manager=self.locale_manager, engine=self.engine)

    @staticmethod
    def export_csv_template(filepath: str, fleet: Optional[Dict[str, RegisteredVehicle]] = None) -> bool:
        return EVPFleetCsvService.export_csv_template(filepath, fleet)

    @staticmethod
    def import_csv_config(filepath: str) -> List[RegisteredVehicle]:
        return EVPFleetCsvService.import_csv_config(filepath)

    @classmethod
    def _get_engine(cls, locale_manager=None, engine=None):
        if engine is not None:
            return engine
        from src.database.db_engine import DatabaseEngine
        from src.utils.paths import get_base_output_dir

        cache_key = (
            f"{get_base_output_dir()}::{os.getenv('CARINA_DB_TYPE', '')}::{os.getenv('CARINA_DB_CONNECTED', '')}"
        )
        with cls._engine_cache_lock:
            cached = cls._engine_cache.get(cache_key)
            if cached is None:
                cached = DatabaseEngine(locale_manager=locale_manager)
                cls._engine_cache[cache_key] = cached
            return cached

    @classmethod
    def save_vehicle_db(cls, vehicle: RegisteredVehicle, locale_manager=None, engine=None) -> bool:
        """Saves or updates an emergency vehicle registration record in PostgreSQL/SQLite database."""
        try:
            eng = cls._get_engine(locale_manager, engine)
            is_pg = getattr(eng, "db_type", "sqlite") == "postgres"
            sql = EVPFleetSql.get_upsert_vehicle_query(is_pg)
            params = (
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
            with db_transaction(eng, commit=True) as (conn, cursor):
                if not conn or not cursor:
                    return False
                cursor.execute(sql, params)
                cursor.execute(EVPFleetSql.get_delete_denied_query(is_pg), (vehicle.vehicle_id,))
            logger.info(
                f"[DB Persistence] Saved EVP vehicle '{vehicle.vehicle_id}' ({vehicle.corporation.value}) to database."
            )
            return True
        except Exception as e:
            logger.error(f"[DB Persistence] Failed to save EVP vehicle to database: {e}", exc_info=True)
            return False

    @classmethod
    def remove_vehicle_db(cls, vehicle_id: str, locale_manager=None, engine=None) -> bool:
        """Deletes the vehicle registration record and adds it to evp_denied_fleet."""
        try:
            eng = cls._get_engine(locale_manager, engine)
            clean_id = str(vehicle_id).strip().upper()
            is_pg = getattr(eng, "db_type", "sqlite") == "postgres"
            with db_transaction(eng, commit=True) as (conn, cursor):
                if not conn or not cursor:
                    return False
                cursor.execute(EVPFleetSql.get_delete_registered_query(is_pg), (clean_id,))
                cursor.execute(EVPFleetSql.get_insert_denied_query(is_pg), (clean_id,))
            logger.info(f"[DB Persistence] Deleted EVP vehicle '{clean_id}' and marked denied in database.")
            return True
        except Exception as e:
            logger.error(f"[DB Persistence] Failed to remove EVP vehicle from database: {e}", exc_info=True)
            return False

    @classmethod
    def load_all_vehicles_db(cls, locale_manager=None, engine=None) -> Dict[str, RegisteredVehicle]:
        """Loads all authorized emergency vehicles from database."""
        fleet: Dict[str, RegisteredVehicle] = {}
        try:
            eng = cls._get_engine(locale_manager, engine)
            with db_transaction(eng, commit=False) as (conn, cursor):
                if not conn or not cursor:
                    return fleet
                cursor.execute(EVPFleetSql.SELECT_ALL_REGISTERED)
                for row in cursor.fetchall():
                    v = RegisteredVehicle(
                        vehicle_id=str(row[0]),
                        corporation=CorporationType.from_string(str(row[1])),
                        plate=str(row[2] or ""),
                        description=str(row[3] or ""),
                        device_id=str(row[4] or ""),
                        ip_address=str(row[5] or ""),
                        port=int(row[6]) if row[6] is not None else 8085,
                        protocol=str(row[7] or "HTTP"),
                        auth_token=str(row[8] or ""),
                        is_active=bool(row[9]),
                    )
                    fleet[v.vehicle_id] = v
            logger.info(f"[DB Persistence] Loaded {len(fleet)} authorized EVP vehicles from database.")
        except Exception as e:
            logger.error(f"[DB Persistence] Failed to load EVP vehicles from database: {e}", exc_info=True)
        return fleet

    @classmethod
    def load_denied_vehicles_db(cls, locale_manager=None, engine=None) -> List[str]:
        """Loads all denied vehicle identifiers from database."""
        denied: List[str] = []
        try:
            eng = cls._get_engine(locale_manager, engine)
            with db_transaction(eng, commit=False) as (conn, cursor):
                if not conn or not cursor:
                    return denied
                cursor.execute(EVPFleetSql.SELECT_ALL_DENIED)
                denied = [str(r[0]) for r in cursor.fetchall()]
        except Exception as e:
            logger.error(f"[DB Persistence] Failed to load denied EVP vehicles from database: {e}", exc_info=True)
        return denied

    @classmethod
    def clear_all_vehicles_db(cls, locale_manager=None, engine=None) -> bool:
        """Deletes all registered fleet vehicle entries completely from database."""
        try:
            eng = cls._get_engine(locale_manager, engine)
            with db_transaction(eng, commit=True) as (conn, cursor):
                if not conn or not cursor:
                    return False
                cursor.execute(EVPFleetSql.CLEAR_ALL_REGISTERED)
                cursor.execute(EVPFleetSql.CLEAR_ALL_DENIED)
            logger.info("[DB Persistence] Cleared all EVP vehicle records and denylists from database.")
            return True
        except Exception as e:
            logger.error(f"[DB Persistence] Failed to clear EVP vehicles in database: {e}", exc_info=True)
            return False
