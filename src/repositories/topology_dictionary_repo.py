# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: src/repositories/topology_dictionary_repo.py
# Author: Gabriel Moraes
# Date: September 2026

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from psycopg2.extras import execute_values

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
        conn = self.engine.get_connection()
        if not conn:
            return False
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS topology_dictionary (
                        id BIGSERIAL PRIMARY KEY,
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
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"[TopologyDictionaryRepo] Error ensuring table exists: {e}")
            try:
                conn.rollback()
            except Exception:
                pass
            return False

    def bulk_save_topology_elements(self, elements: List[Dict[str, Any]]) -> bool:
        """Saves or updates topology dictionary elements in PostgreSQL."""
        if not elements:
            return True
        conn = self.engine.get_connection()
        if not conn:
            return False

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

        query = """
            INSERT INTO topology_dictionary (
                element_type, raw_net_id, numeric_id, custom_name, from_node, to_node, is_bidirectional_pair
            ) VALUES %s
            ON CONFLICT (raw_net_id) DO UPDATE SET
                numeric_id = EXCLUDED.numeric_id,
                from_node = EXCLUDED.from_node,
                to_node = EXCLUDED.to_node,
                is_bidirectional_pair = EXCLUDED.is_bidirectional_pair;
        """
        try:
            with conn.cursor() as cursor:
                execute_values(cursor, query, batch, page_size=500)
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"[TopologyDictionaryRepo] Bulk save topology elements failed: {e}")
            try:
                conn.rollback()
            except Exception:
                pass
            return False

    def update_topology_custom_name(self, element_type: str, raw_net_id: str, new_name: str) -> bool:
        """Updates user configured custom name for a street or intersection in PostgreSQL."""
        conn = self.engine.get_connection()
        if not conn:
            return False
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE topology_dictionary
                    SET custom_name = %s
                    WHERE UPPER(element_type) = UPPER(%s) AND raw_net_id = %s;
                    """,
                    (new_name, element_type, raw_net_id),
                )
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"[TopologyDictionaryRepo] Failed to update custom name for {raw_net_id}: {e}")
            try:
                conn.rollback()
            except Exception:
                pass
            return False

    def get_topology_custom_name(self, element_type: str, raw_net_id: str) -> Optional[str]:
        """Queries custom user-configured name for a street or intersection from PostgreSQL."""
        conn = self.engine.get_connection()
        if not conn:
            return None
        try:
            with conn.cursor() as cursor:
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
