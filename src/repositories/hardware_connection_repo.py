# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Relational Database Repository for hardware controller connection configs (Clean Architecture / DIP).
Implements IConnectionConfigRepository in src/repositories/, unifying PostgreSQL and SQLite SQL handling.
"""

import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class HardwareConnectionRepository:
    """Persists hardware controller auto-connect and SNMPv2c/v3 metadata in SQLite/PostgreSQL."""

    def __init__(self, locale_manager: Any = None, engine: Optional[Any] = None) -> None:
        self._locale_manager = locale_manager
        self._default_engine = engine

    def _resolve_engine(self, engine: Optional[Any] = None, locale_manager: Any = None) -> Any:
        if engine is not None:
            return engine
        if self._default_engine is not None:
            return self._default_engine
        from src.database.db_engine import DatabaseEngine

        return DatabaseEngine(locale_manager=locale_manager or self._locale_manager)

    @staticmethod
    def _is_postgres(engine: Any) -> bool:
        return getattr(engine, "db_type", "sqlite") == "postgres"

    @staticmethod
    def _ensure_snmp_column(cursor: Any, engine: Any) -> None:
        """Idempotently ensures optional snmp_config column exists on legacy DB schemas."""
        try:
            if HardwareConnectionRepository._is_postgres(engine):
                cursor.execute("ALTER TABLE hardware_controller_connections ADD COLUMN IF NOT EXISTS snmp_config TEXT;")
            else:
                cursor.execute("PRAGMA table_info(hardware_controller_connections);")
                cols = {row[1] for row in cursor.fetchall()}
                if cols and "snmp_config" not in cols:
                    cursor.execute("ALTER TABLE hardware_controller_connections ADD COLUMN snmp_config TEXT;")
        except Exception as exc:
            logger.debug(f"[DB Persistence] Ignoring optional snmp_config column check: {exc}")

    def save_connection_db(
        self,
        intersection_id: str,
        ip_address: str,
        locale_manager: Any = None,
        engine: Optional[Any] = None,
        snmp_config: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Saves or updates an intersection IP/SNMP connection record."""
        conn = None
        try:
            eng = self._resolve_engine(engine, locale_manager)
            conn = eng.get_connection()
            if not conn:
                return False
            cursor = conn.cursor()
            is_pg = self._is_postgres(eng)
            ph = "%s" if is_pg else "?"
            now_expr = "NOW()" if is_pg else "CURRENT_TIMESTAMP"
            conflict_target = "(intersection_id)" if is_pg else "(intersection_id)"
            ref = "EXCLUDED" if is_pg else "excluded"

            if snmp_config is not None:
                self._ensure_snmp_column(cursor, eng)
                snmp_json = json.dumps(snmp_config)
                sql = (
                    f"INSERT INTO hardware_controller_connections "
                    f"(intersection_id, ip_address, auto_connect, last_connected, snmp_config) "
                    f"VALUES ({ph}, {ph}, TRUE, {now_expr}, {ph}) "
                    f"ON CONFLICT {conflict_target} "
                    f"DO UPDATE SET ip_address = {ref}.ip_address, auto_connect = TRUE, "
                    f"last_connected = {now_expr}, snmp_config = {ref}.snmp_config;"
                )
                cursor.execute(sql, (str(intersection_id), str(ip_address), snmp_json))
            else:
                sql = (
                    f"INSERT INTO hardware_controller_connections "
                    f"(intersection_id, ip_address, auto_connect, last_connected) "
                    f"VALUES ({ph}, {ph}, TRUE, {now_expr}) "
                    f"ON CONFLICT {conflict_target} "
                    f"DO UPDATE SET ip_address = {ref}.ip_address, auto_connect = TRUE, "
                    f"last_connected = {now_expr};"
                )
                cursor.execute(sql, (str(intersection_id), str(ip_address)))

            conn.commit()
            logger.info(f"[DB Persistence] Saved hardware connection for '{intersection_id}' at {ip_address}")
            return True
        except Exception as exc:
            logger.error(f"[DB Persistence] Failed to save hardware connection to database: {exc}", exc_info=True)
            return False
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass

    def remove_connection_db(
        self,
        intersection_id: str,
        locale_manager: Any = None,
        engine: Optional[Any] = None,
    ) -> bool:
        """Deletes both raw and tl_-prefixed connection records for an intersection."""
        conn = None
        try:
            eng = self._resolve_engine(engine, locale_manager)
            conn = eng.get_connection()
            if not conn:
                return False
            cursor = conn.cursor()

            clean_id = str(intersection_id).strip()
            alt_id = clean_id.replace("tl_", "") if clean_id.startswith("tl_") else f"tl_{clean_id}"
            ph = "%s" if self._is_postgres(eng) else "?"
            cursor.execute(
                f"DELETE FROM hardware_controller_connections WHERE intersection_id = {ph} OR intersection_id = {ph};",
                (clean_id, alt_id),
            )
            conn.commit()
            logger.info(f"[DB Persistence] Deleted connection record for '{clean_id}' and '{alt_id}' from database.")
            return True
        except Exception as exc:
            logger.error(f"[DB Persistence] Failed to delete hardware connection from database: {exc}", exc_info=True)
            return False
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass

    def load_connection_configs_with_snmp_db(
        self,
        locale_manager: Any = None,
        engine: Optional[Any] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Loads auto-connect hardware entries including optional SNMPv2c/v3 metadata."""
        configs: Dict[str, Dict[str, Any]] = {}
        conn = None
        try:
            eng = self._resolve_engine(engine, locale_manager)
            conn = eng.get_connection()
            if not conn:
                return configs
            cursor = conn.cursor()
            self._ensure_snmp_column(cursor, eng)
            try:
                cursor.execute(
                    "SELECT intersection_id, ip_address, snmp_config FROM hardware_controller_connections WHERE auto_connect = TRUE;"
                )
                for row in cursor.fetchall():
                    parsed_snmp = None
                    if len(row) > 2 and row[2]:
                        try:
                            raw_parsed = json.loads(row[2]) if isinstance(row[2], str) else row[2]
                            if isinstance(raw_parsed, dict):
                                parsed_snmp = raw_parsed
                        except Exception:
                            parsed_snmp = None
                    configs[str(row[0])] = {"ip": str(row[1]), "snmp_config": parsed_snmp}
            except Exception:
                cursor.execute(
                    "SELECT intersection_id, ip_address FROM hardware_controller_connections WHERE auto_connect = TRUE;"
                )
                for row in cursor.fetchall():
                    configs[str(row[0])] = {"ip": str(row[1]), "snmp_config": None}
            logger.info(f"[DB Persistence] Loaded {len(configs)} saved hardware connection configs from database.")
        except Exception as exc:
            logger.error(f"[DB Persistence] Failed to load hardware connections from database: {exc}", exc_info=True)
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
        return configs

    def load_all_snmp_configs_db(
        self,
        locale_manager: Any = None,
        engine: Optional[Any] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Loads optional SNMPv2c/v3 config dicts keyed by intersection_id."""
        detailed = self.load_connection_configs_with_snmp_db(locale_manager=locale_manager, engine=engine)
        return {tl_id: entry["snmp_config"] for tl_id, entry in detailed.items() if entry.get("snmp_config")}

    def load_all_connections_db(
        self,
        locale_manager: Any = None,
        engine: Optional[Any] = None,
    ) -> Dict[str, str]:
        """Loads all saved auto-connect hardware {intersection_id: ip_address} pairs."""
        detailed = self.load_connection_configs_with_snmp_db(locale_manager=locale_manager, engine=engine)
        return {tl_id: entry["ip"] for tl_id, entry in detailed.items()}

    def clear_all_connections_db(
        self,
        locale_manager: Any = None,
        engine: Optional[Any] = None,
    ) -> bool:
        """Deletes all hardware connection entries completely from the database."""
        conn = None
        try:
            eng = self._resolve_engine(engine, locale_manager)
            conn = eng.get_connection()
            if not conn:
                return False
            cursor = conn.cursor()
            cursor.execute("DELETE FROM hardware_controller_connections;")
            conn.commit()
            logger.info("[DB Persistence] Cleared (deleted) all hardware connection records from database.")
            return True
        except Exception as exc:
            logger.error(f"[DB Persistence] Failed to clear hardware connections in database: {exc}", exc_info=True)
            return False
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
