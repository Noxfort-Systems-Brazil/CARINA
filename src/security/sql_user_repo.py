# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
SQL Database User Repository Component (SOLID: SRP & DIP).
Supports both PostgreSQL and SQLite transparently via DatabaseEngine or raw DB connections.
"""

from contextlib import contextmanager
import logging
from typing import Any, Dict, Generator, List, Optional

from src.security.interfaces import ISecurityStateRepository, IUserRepository
from src.security.sql_security_state_repo import SqlSecurityStateRepository

logger = logging.getLogger("SqlUserRepository")


class SqlUserRepository(IUserRepository):
    """
    SQL-based implementation of IUserRepository.
    Supports both PostgreSQL and SQLite transparently with atomic transactions.
    """

    STATE_ID = "global_lockdown"

    def __init__(
        self,
        engine: Any,
        locale_manager: Optional[object] = None,
        security_state_repo: Optional[ISecurityStateRepository] = None,
    ):
        self.engine = engine
        self.locale_manager = locale_manager
        self.security_state_repo = security_state_repo or SqlSecurityStateRepository(engine, locale_manager)
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

    def is_available(self) -> bool:
        """Returns True if the underlying database engine is connected and ready."""
        if not self.engine:
            return False
        return bool(getattr(self.engine, "is_connected", True))

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
            logger.error(f"[SqlUserRepository] Database transaction error: {e}", exc_info=True)
            raise
        finally:
            if conn and hasattr(self.engine, "get_connection") and hasattr(conn, "close"):
                if conn is not self.engine and not getattr(self.engine, "is_shared_connection", False):
                    try:
                        conn.close()
                    except Exception:
                        pass

    def ensure_storage(self) -> None:
        """Ensures that the required tables exist in the target database."""
        try:
            with self._connection() as conn:
                if not conn:
                    return
                cursor = conn.cursor()
                try:
                    if self.is_postgres:
                        cursor.execute(
                            """
                            CREATE TABLE IF NOT EXISTS system_users (
                                id SERIAL PRIMARY KEY,
                                username VARCHAR(64) UNIQUE NOT NULL,
                                password_hash VARCHAR(255) NOT NULL,
                                role VARCHAR(32) NOT NULL DEFAULT 'OPERATOR',
                                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                            );
                            """
                        )
                    else:
                        cursor.execute(
                            """
                            CREATE TABLE IF NOT EXISTS system_users (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                username TEXT UNIQUE NOT NULL,
                                password_hash TEXT NOT NULL,
                                role TEXT NOT NULL DEFAULT 'OPERATOR',
                                is_active BOOLEAN NOT NULL DEFAULT 1,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                            );
                            """
                        )
                finally:
                    cursor.close()
            if self.security_state_repo:
                self.security_state_repo.ensure_storage()
        except Exception as e:
            logger.warning(f"[SqlUserRepository] Could not ensure tables: {e}", exc_info=True)

    def _ensure_tables(self) -> None:
        """Alias for backward compatibility."""
        self.ensure_storage()

    # --- Modern IUserRepository Contracts ---

    def fetch_users(self) -> Dict[str, Dict[str, str]]:
        """Loads all registered users as username -> {'hash': ..., 'role': ...}."""
        try:
            with self._connection() as conn:
                if not conn:
                    return {}
                cursor = conn.cursor()
                try:
                    cursor.execute("SELECT username, password_hash, role FROM system_users WHERE is_active = 1 OR is_active = TRUE;")
                    rows = cursor.fetchall()
                    return {r[0]: {"hash": r[1], "role": r[2]} for r in rows}
                finally:
                    cursor.close()
        except Exception as e:
            logger.error(f"[SqlUserRepository] Error fetching users: {e}", exc_info=True)
            return {}

    def save_user(self, username: str, password_hash: str, role: str) -> bool:
        """Persists or updates a user credential record."""
        self.set_user(username, password_hash, role)
        return True

    def delete_user(self, username: str) -> bool:
        """Deletes a user record by username."""
        try:
            with self._connection() as conn:
                if not conn:
                    return False
                cursor = conn.cursor()
                try:
                    cursor.execute(f"DELETE FROM system_users WHERE username = {self.placeholder};", (username,))
                    deleted = cursor.rowcount > 0
                    return deleted
                finally:
                    cursor.close()
        except Exception as e:
            logger.error(f"[SqlUserRepository] Error deleting user '{username}': {e}", exc_info=True)
            return False

    # --- Backward-Compatibility Contracts for CARINA Legacy Callers ---

    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        try:
            with self._connection() as conn:
                if not conn:
                    return None
                cursor = conn.cursor()
                try:
                    cursor.execute(
                        f"SELECT password_hash, role FROM system_users WHERE username = {self.placeholder} AND (is_active = 1 OR is_active = TRUE);",
                        (username,),
                    )
                    row = cursor.fetchone()
                    if row:
                        return {"hash": row[0], "role": row[1]}
                    return None
                finally:
                    cursor.close()
        except Exception as e:
            logger.error(f"[SqlUserRepository] Error getting user '{username}': {e}", exc_info=True)
            return None

    def set_user(self, username: str, password_hash: str, role: str) -> bool:
        """Creates or updates a user record. Returns True if updated, False if newly created."""
        existing = self.get_user(username)
        is_update = existing is not None
        try:
            with self._connection() as conn:
                if not conn:
                    return False
                cursor = conn.cursor()
                try:
                    if is_update:
                        cursor.execute(
                            f"UPDATE system_users SET password_hash = {self.placeholder}, role = {self.placeholder}, updated_at = CURRENT_TIMESTAMP WHERE username = {self.placeholder};",
                            (password_hash, role, username),
                        )
                    else:
                        cursor.execute(
                            f"INSERT INTO system_users (username, password_hash, role) VALUES ({self.placeholder}, {self.placeholder}, {self.placeholder});",
                            (username, password_hash, role),
                        )
                    return is_update
                finally:
                    cursor.close()
        except Exception as e:
            logger.error(f"[SqlUserRepository] Error setting user '{username}': {e}", exc_info=True)
            return is_update

    def list_users(self) -> List[Dict[str, Any]]:
        try:
            with self._connection() as conn:
                if not conn:
                    return []
                cursor = conn.cursor()
                try:
                    cursor.execute(
                        "SELECT username, role FROM system_users WHERE is_active = 1 OR is_active = TRUE ORDER BY id ASC;"
                    )
                    rows = cursor.fetchall()
                    return [{"username": row[0], "role": row[1]} for row in rows]
                finally:
                    cursor.close()
        except Exception as e:
            logger.error(f"[SqlUserRepository] Error listing users: {e}", exc_info=True)
            return []

    def get_failed_attempts(self) -> int:
        if self.security_state_repo:
            return self.security_state_repo.get_failed_attempts()
        return 0

    def increment_failed_attempts(self) -> int:
        if self.security_state_repo:
            return self.security_state_repo.increment_failed_attempts()
        return 1

    def reset_failed_attempts(self) -> None:
        if self.security_state_repo:
            self.security_state_repo.reset_failed_attempts()

    def ensure_default_user(self, is_production: bool, master_user: str, default_hash: str) -> None:
        self.ensure_storage()
        if not self.list_users():
            if not (is_production and master_user != "admin"):
                self.set_user("admin", default_hash, "SUPERUSER")
