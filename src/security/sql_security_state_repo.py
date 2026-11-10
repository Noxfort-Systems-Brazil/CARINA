# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
SQL Database Security State Repository Component (SOLID: SRP & DIP, DDD Aggregate).
Manages persistent system security state (rate limiting, failed attempts, and lockdown).
"""

from contextlib import contextmanager
import logging
from typing import Any, Generator, Optional

from src.security.interfaces import ISecurityStateRepository

logger = logging.getLogger("SqlSecurityStateRepository")


class SqlSecurityStateRepository(ISecurityStateRepository):
    """
    SQL-based implementation of ISecurityStateRepository.
    Encapsulates persistent failed attempts counter and system lockdown state.
    """

    STATE_ID = "global_lockdown"

    def __init__(self, engine: Any, locale_manager: Optional[object] = None):
        self.engine = engine
        self.locale_manager = locale_manager
        self.ensure_storage()

    @property
    def is_postgres(self) -> bool:
        """Determines whether the active engine uses PostgreSQL or SQLite."""
        if not self.engine:
            return False
        return getattr(self.engine, "db_type", "sqlite") == "postgres"

    @property
    def placeholder(self) -> str:
        """Returns the correct parameter placeholder for queries (%s for PostgreSQL, ? for SQLite)."""
        return "%s" if self.is_postgres else "?"

    @contextmanager
    def _connection(self) -> Generator[Any, None, None]:
        """Provides an active database connection and ensures commits/closes."""
        if not self.engine:
            yield None
            return

        conn = None
        try:
            if hasattr(self.engine, "get_connection"):
                conn = self.engine.get_connection()
            else:
                conn = self.engine

            if conn is None:
                yield None
                return

            yield conn
            if hasattr(conn, "commit"):
                conn.commit()
        except Exception as e:
            if conn and hasattr(conn, "rollback"):
                try:
                    conn.rollback()
                except Exception:
                    pass
            logger.error(f"[SqlSecurityStateRepository] Database transaction error: {e}", exc_info=True)
            raise
        finally:
            if conn and hasattr(self.engine, "get_connection") and hasattr(conn, "close"):
                if conn is not self.engine and not getattr(self.engine, "is_shared_connection", False):
                    try:
                        conn.close()
                    except Exception:
                        pass

    def ensure_storage(self) -> None:
        """Ensures that system_security_state table exists."""
        try:
            with self._connection() as conn:
                if not conn:
                    return
                cursor = conn.cursor()
                try:
                    if self.is_postgres:
                        cursor.execute(
                            """
                            CREATE TABLE IF NOT EXISTS system_security_state (
                                id VARCHAR(32) PRIMARY KEY,
                                failed_attempts INTEGER NOT NULL DEFAULT 0,
                                is_locked BOOLEAN NOT NULL DEFAULT FALSE,
                                locked_until TIMESTAMP,
                                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                            );
                            """
                        )
                    else:
                        cursor.execute(
                            """
                            CREATE TABLE IF NOT EXISTS system_security_state (
                                id TEXT PRIMARY KEY,
                                failed_attempts INTEGER NOT NULL DEFAULT 0,
                                is_locked BOOLEAN NOT NULL DEFAULT 0,
                                locked_until TIMESTAMP,
                                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                            );
                            """
                        )
                finally:
                    cursor.close()
        except Exception as e:
            logger.warning(f"[SqlSecurityStateRepository] Could not ensure storage: {e}", exc_info=True)

    def get_failed_attempts(self) -> int:
        """Returns the recorded count of failed authentication attempts."""
        try:
            with self._connection() as conn:
                if not conn:
                    return 0
                cursor = conn.cursor()
                try:
                    cursor.execute(
                        f"SELECT failed_attempts FROM system_security_state WHERE id = {self.placeholder};",
                        (self.STATE_ID,),
                    )
                    row = cursor.fetchone()
                    return int(row[0]) if row else 0
                finally:
                    cursor.close()
        except Exception as e:
            logger.error(f"[SqlSecurityStateRepository] Error getting failed attempts: {e}", exc_info=True)
            return 0

    def increment_failed_attempts(self) -> int:
        """Increments failed attempt counter atomically and returns the new count."""
        try:
            with self._connection() as conn:
                if not conn:
                    return 1
                cursor = conn.cursor()
                try:
                    cursor.execute(
                        f"SELECT failed_attempts FROM system_security_state WHERE id = {self.placeholder};",
                        (self.STATE_ID,),
                    )
                    row = cursor.fetchone()
                    if row is None:
                        new_count = 1
                        cursor.execute(
                            f"INSERT INTO system_security_state (id, failed_attempts) VALUES ({self.placeholder}, {self.placeholder});",
                            (self.STATE_ID, new_count),
                        )
                    else:
                        new_count = int(row[0]) + 1
                        cursor.execute(
                            f"UPDATE system_security_state SET failed_attempts = {self.placeholder}, updated_at = CURRENT_TIMESTAMP WHERE id = {self.placeholder};",
                            (new_count, self.STATE_ID),
                        )
                    return new_count
                finally:
                    cursor.close()
        except Exception as e:
            logger.error(f"[SqlSecurityStateRepository] Error incrementing failed attempts: {e}", exc_info=True)
            return 1

    def reset_failed_attempts(self) -> None:
        """Resets failed attempts to 0."""
        try:
            with self._connection() as conn:
                if not conn:
                    return
                cursor = conn.cursor()
                try:
                    cursor.execute(
                        f"UPDATE system_security_state SET failed_attempts = 0, updated_at = CURRENT_TIMESTAMP WHERE id = {self.placeholder};",
                        (self.STATE_ID,),
                    )
                finally:
                    cursor.close()
        except Exception as e:
            logger.error(f"[SqlSecurityStateRepository] Error resetting failed attempts: {e}", exc_info=True)
