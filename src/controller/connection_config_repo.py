# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Backward-compatible controller facade delegating CSV operations to ConnectionCSVStore
and SQL operations to HardwareConnectionRepository (Clean Architecture / SRP).
"""

from typing import Any, Dict, List, Optional

from src.repositories.connection_csv_store import ConnectionCSVStore
from src.repositories.hardware_connection_repo import HardwareConnectionRepository


class ConnectionConfigRepository:
    """Legacy static facade forwarding CSV and DB connection persistence to src/repositories/."""

    _csv_store = ConnectionCSVStore()
    _db_repo = HardwareConnectionRepository()

    @classmethod
    def export_csv_template(cls, filepath: str, saved_ips: Dict[str, str], known_intersections: List[str]) -> bool:
        return cls._csv_store.export_csv_template(filepath, saved_ips, known_intersections)

    @classmethod
    def import_csv_entries(cls, filepath: str) -> Dict[str, Dict[str, Any]]:
        return cls._csv_store.import_csv_entries(filepath)

    @classmethod
    def import_csv_config(cls, filepath: str) -> Dict[str, str]:
        entries = cls.import_csv_entries(filepath)
        return {tl_id: entry["ip"] for tl_id, entry in entries.items()}

    @classmethod
    def save_connection_db(
        cls,
        intersection_id: str,
        ip_address: str,
        locale_manager: Any = None,
        engine: Optional[Any] = None,
        snmp_config: Optional[Dict[str, Any]] = None,
    ) -> bool:
        return cls._db_repo.save_connection_db(
            intersection_id=intersection_id,
            ip_address=ip_address,
            locale_manager=locale_manager,
            engine=engine,
            snmp_config=snmp_config,
        )

    @classmethod
    def remove_connection_db(
        cls, intersection_id: str, locale_manager: Any = None, engine: Optional[Any] = None
    ) -> bool:
        return cls._db_repo.remove_connection_db(
            intersection_id=intersection_id,
            locale_manager=locale_manager,
            engine=engine,
        )

    @classmethod
    def load_connection_configs_with_snmp_db(
        cls, locale_manager: Any = None, engine: Optional[Any] = None
    ) -> Dict[str, Dict[str, Any]]:
        return cls._db_repo.load_connection_configs_with_snmp_db(
            locale_manager=locale_manager,
            engine=engine,
        )

    @classmethod
    def load_all_snmp_configs_db(
        cls, locale_manager: Any = None, engine: Optional[Any] = None
    ) -> Dict[str, Dict[str, Any]]:
        detailed = cls.load_connection_configs_with_snmp_db(locale_manager=locale_manager, engine=engine)
        return {tl_id: entry["snmp_config"] for tl_id, entry in detailed.items() if entry.get("snmp_config")}

    @classmethod
    def load_all_connections_db(cls, locale_manager: Any = None, engine: Optional[Any] = None) -> Dict[str, str]:
        detailed = cls.load_connection_configs_with_snmp_db(locale_manager=locale_manager, engine=engine)
        return {tl_id: entry["ip"] for tl_id, entry in detailed.items()}

    @classmethod
    def clear_all_connections_db(cls, locale_manager: Any = None, engine: Optional[Any] = None) -> bool:
        return cls._db_repo.clear_all_connections_db(
            locale_manager=locale_manager,
            engine=engine,
        )
