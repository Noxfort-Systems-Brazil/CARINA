# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Transactional Database Executor for the EVP subsystem (DIP / Clean Architecture).
Encapsulates connection lifecycle, cursors, and commits for PostgreSQL and SQLite.
"""

from contextlib import contextmanager
import logging
from typing import Any, Callable, Generator, Optional

logger = logging.getLogger(__name__)


class EVPDatabaseExecutor:
    """Manages connections and safe transaction execution for EVP repositories."""

    def __init__(self, engine: Any, close_conn_fn: Optional[Callable[[Any], None]] = None):
        self.engine = engine
        self._close_conn = close_conn_fn

    @property
    def is_postgres(self) -> bool:
        """Determines whether the active engine uses PostgreSQL or SQLite."""
        if not self.engine:
            return False
        return getattr(self.engine, "db_type", "sqlite") == "postgres"

    @contextmanager
    def transaction(self) -> Generator[Any, None, None]:
        """
        Context manager providing an active cursor with auto-commit and safe cleanup.
        Yields the cursor for the `with` block and closes the connection in `finally`.
        """
        if not self.engine:
            yield None
            return

        conn = None
        try:
            conn = self.engine.get_connection()
            if not conn:
                yield None
                return

            cursor = conn.cursor()
            try:
                yield cursor
                if hasattr(conn, "commit"):
                    conn.commit()
            finally:
                try:
                    cursor.close()
                except Exception as _exc:
                    logger.debug("[evp] Ignored recoverable error: %s", _exc)
        except Exception as e:
            logger.error(f"[EVPDatabaseExecutor] Erro durante transação de banco de dados: {e}", exc_info=True)
            raise
        finally:
            if conn is not None and self._close_conn:
                try:
                    self._close_conn(conn)
                except Exception as _exc:
                    logger.debug("[evp] Ignored recoverable error: %s", _exc)
