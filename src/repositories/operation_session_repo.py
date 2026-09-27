# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: src/repositories/operation_session_repo.py
# Author: Gabriel Moraes
# Date: September 2026

import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from src.database.db_engine import DatabaseEngine


class OperationSessionRepository:
    """
    Dedicated repository for managing operational sessions lifecycle in PostgreSQL.
    Follows Single Responsibility Principle (SRP).
    """

    def __init__(self, engine: "DatabaseEngine"):
        self.engine = engine
        self.ensure_table_exists()

    def ensure_table_exists(self) -> bool:
        """Ensures that the operation_sessions table exists."""
        conn = self.engine.get_connection()
        if not conn:
            return False
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS operation_sessions (
                        session_id BIGSERIAL PRIMARY KEY,
                        start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        end_time TIMESTAMP,
                        status VARCHAR(50) DEFAULT 'EM_OPERACAO',
                        error_message TEXT
                    );
                    """
                )
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"[OperationSessionRepo] Error ensuring table exists: {e}")
            try:
                conn.rollback()
            except Exception:
                pass
            return False

    def start_session(self) -> Optional[int]:
        """Registers a new operational session start_time in PostgreSQL."""
        conn = self.engine.get_connection()
        if not conn:
            return None
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO operation_sessions (start_time, status)
                    VALUES (CURRENT_TIMESTAMP, 'EM_OPERACAO')
                    RETURNING session_id;
                    """
                )
                sid = cursor.fetchone()[0]
            conn.commit()
            return sid
        except Exception as e:
            logging.error(f"[OperationSessionRepo] Error starting operation session: {e}")
            try:
                conn.rollback()
            except Exception:
                pass
            return None

    def end_session(self, session_id: int, status: str = "FINALIZADO_NORMAL", error_msg: Optional[str] = None) -> bool:
        """Updates operation session end_time and status in PostgreSQL."""
        conn = self.engine.get_connection()
        if not conn or not session_id:
            return False
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE operation_sessions
                    SET end_time = CURRENT_TIMESTAMP, status = %s, error_message = %s
                    WHERE session_id = %s;
                    """,
                    (status, error_msg, session_id),
                )
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"[OperationSessionRepo] Error ending operation session {session_id}: {e}")
            try:
                conn.rollback()
            except Exception:
                pass
            return False
