# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from src.database.connection_pool import db_transaction

try:
    from psycopg2.extras import execute_values
except ImportError:
    execute_values = None

if TYPE_CHECKING:
    from src.database.db_engine import DatabaseEngine


class TopologyDictionaryRepository:
    """
    Dedicated repository for managing SUMO network topology dictionaries and custom aliases.
    Follows Single Responsibility Principle (SRP).
    """

    def __init__(self, engine: "DatabaseEngine"):
        self.engine = engine
        self.ensure_table_exists()

    def ensure_table_exists(self) -> bool:
        """Ensures that the topology_dictionary table exists."""
        is_pg = getattr(self.engine, "db_type", "sqlite") == "postgres"
        try:
            with db_transaction(self.engine, commit=True) as (conn, cursor):
                if not conn or not cursor:
                    return False
                pk_type = "BIGSERIAL PRIMARY KEY" if is_pg else "INTEGER PRIMARY KEY AUTOINCREMENT"
                cursor.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS topology_dictionary (
                        id {pk_type},
                        element_type VARCHAR(20) NOT NULL,
                        raw_net_id VARCHAR(255) UNIQUE NOT NULL,
                        numeric_id BIGINT NOT NULL,
                        custom_name VARCHAR(255) NOT NULL,
                        from_node VARCHAR(100),
                        to_node VARCHAR(100),
                        is_bidirectional_pair BOOLEAN DEFAULT FALSE
                    );
                    """
                )
            return True
        except Exception as e:
            logging.error(f"[TopologyDictionaryRepo] Error ensuring table exists: {e}", exc_info=True)
            return False

    def bulk_save_topology_elements(self, elements: List[Dict[str, Any]]) -> bool:
        """Saves or updates topology dictionary elements in PostgreSQL or SQLite."""
        if not elements:
            return True

        batch = [
            (
                el["element_type"],
                el["raw_net_id"],
                int(el["numeric_id"]),
                el["custom_name"],
                el.get("from_node"),
                el.get("to_node"),
                bool(el.get("is_bidirectional_pair", False)),
            )
            for el in elements
        ]

        try:
            with db_transaction(self.engine, commit=True) as (conn, cursor):
                if not conn or not cursor:
                    return False
                if getattr(self.engine, "db_type", "sqlite") == "postgres":
                    from psycopg2.extras import execute_values

                    query_pg = """
                        INSERT INTO topology_dictionary (
                            element_type, raw_net_id, numeric_id, custom_name, from_node, to_node, is_bidirectional_pair
                        ) VALUES %s
                        ON CONFLICT (raw_net_id) DO UPDATE SET
                            custom_name = EXCLUDED.custom_name,
                            numeric_id = EXCLUDED.numeric_id,
                            from_node = EXCLUDED.from_node,
                            to_node = EXCLUDED.to_node,
                            is_bidirectional_pair = EXCLUDED.is_bidirectional_pair;
                    """
                    execute_values(cursor, query_pg, batch, page_size=500)
                else:
                    query_sqlite = """
                        INSERT INTO topology_dictionary (
                            element_type, raw_net_id, numeric_id, custom_name, from_node, to_node, is_bidirectional_pair
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT (raw_net_id) DO UPDATE SET
                            custom_name = excluded.custom_name,
                            numeric_id = excluded.numeric_id,
                            from_node = excluded.from_node,
                            to_node = excluded.to_node,
                            is_bidirectional_pair = excluded.is_bidirectional_pair;
                    """
                    cursor.executemany(query_sqlite, batch)
            return True
        except Exception as e:
            logging.error(f"[TopologyDictionaryRepo] Bulk save topology elements failed: {e}", exc_info=True)
            return False

    def update_topology_custom_name(self, element_type: str, raw_net_id: str, new_name: str) -> bool:
        """Updates user configured custom name for a street or intersection in PostgreSQL."""
        try:
            with db_transaction(self.engine, commit=True) as (conn, cursor):
                if not conn or not cursor:
                    return False
                cursor.execute(
                    """
                    UPDATE topology_dictionary
                    SET custom_name = %s
                    WHERE UPPER(element_type) = UPPER(%s) AND raw_net_id = %s;
                    """,
                    (new_name, element_type, raw_net_id),
                )
            return True
        except Exception as e:
            logging.error(f"[TopologyDictionaryRepo] Failed to update custom name for {raw_net_id}: {e}", exc_info=True)
            return False

    def get_topology_custom_name(self, element_type: str, raw_net_id: str) -> Optional[str]:
        """Queries custom user-configured name for a street or intersection from PostgreSQL."""
        try:
            with db_transaction(self.engine, commit=False) as (conn, cursor):
                if not conn or not cursor:
                    return None
                cursor.execute(
                    """
                    SELECT custom_name FROM topology_dictionary
                    WHERE UPPER(element_type) = UPPER(%s) AND (raw_net_id = %s OR numeric_id = %s);
                    """,
                    (element_type, raw_net_id, self._to_int_id(raw_net_id)),
                )
                row = cursor.fetchone()
                return str(row[0]) if row and row[0] else None
        except Exception:
            return None

    @staticmethod
    def _to_int_id(val: Any) -> int:
        """Extracts integer numeric digits from agent_id string/int."""
        if isinstance(val, int):
            return val
        s = str(val or "")
        digits = "".join([c for c in s if c.isdigit()])
        if digits:
            return int(digits)
        return abs(hash(s)) % (10**10)
