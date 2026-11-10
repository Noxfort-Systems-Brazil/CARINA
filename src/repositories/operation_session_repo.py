# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

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
            logging.error(f"[OperationSessionRepo] Error ensuring table exists: {e}", exc_info=True)
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
            logging.error(f"[OperationSessionRepo] Error starting operation session: {e}", exc_info=True)
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
            logging.error(f"[OperationSessionRepo] Error ending operation session {session_id}: {e}", exc_info=True)
            try:
                conn.rollback()
            except Exception:
                pass
            return False
