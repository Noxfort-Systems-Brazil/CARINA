# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Thread-safe Database Connection Pooling, SQLite WAL Configuration, and Safe Transactions.

Eliminates SQLite `database is locked` contention via WAL journaling + busy_timeout
and prevents PostgreSQL/SQLite descriptor leaks via pooled proxy cleanup and
deterministic `try/finally` transaction context helpers.
"""

import logging
import threading
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, Generator, Optional, Set, Tuple

logger = logging.getLogger(__name__)

_WAL_LOCK = threading.Lock()
_WAL_INITIALIZED_PATHS: Set[str] = set()


class PooledPostgresConnectionProxy:
    """Wraps a pooled psycopg2 connection so `.close()` safely returns it to the pool."""

    def __init__(self, pool: Any, raw_conn: Any) -> None:
        self._pool = pool
        self._raw = raw_conn
        self._closed = False

    def __enter__(self) -> "PooledPostgresConnectionProxy":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type is not None:
            try:
                self.rollback()
            except Exception:
                pass
        self.close()

    def close(self) -> None:
        if self._closed or self._raw is None:
            return
        self._closed = True
        broken = bool(getattr(self._raw, "closed", 0))
        if not broken and hasattr(self._raw, "rollback"):
            try:
                self._raw.rollback()
            except Exception:
                broken = True
        try:
            self._pool.putconn(self._raw, close=broken)
        except Exception as exc:
            logger.debug("[DB_POOL] Fallback raw connection close after putconn error: %s", exc)
            try:
                self._raw.close()
            except Exception:
                pass
        self._raw = None

    def __getattr__(self, name: str) -> Any:
        if self._raw is None:
            raise RuntimeError("Operation attempted on closed pooled PostgreSQL connection")
        return getattr(self._raw, name)


class PostgresConnectionPool:
    """Lazy thread-safe PostgreSQL connection pool built atop psycopg2.pool."""

    def __init__(self, connect_kwargs_provider: Callable[[], Dict[str, Any]], minconn: int = 1, maxconn: int = 16):
        self._kwargs_provider = connect_kwargs_provider
        self._minconn = minconn
        self._maxconn = maxconn
        self._lock = threading.Lock()
        self._pool: Optional[Any] = None

    def _ensure_pool(self) -> Any:
        if self._pool is not None:
            return self._pool
        from psycopg2 import pool as pg_pool

        kwargs = self._kwargs_provider()
        self._pool = pg_pool.ThreadedConnectionPool(self._minconn, self._maxconn, **kwargs)
        return self._pool

    def acquire(self) -> PooledPostgresConnectionProxy:
        with self._lock:
            pool = self._ensure_pool()
            raw_conn = pool.getconn()
        # Reset idle/stale transaction state before handing out to caller
        if hasattr(raw_conn, "rollback"):
            try:
                raw_conn.rollback()
            except Exception:
                pass
        return PooledPostgresConnectionProxy(pool, raw_conn)

    def close_all(self) -> None:
        with self._lock:
            if self._pool is not None:
                try:
                    self._pool.closeall()
                except Exception as exc:
                    logger.debug("[DB_POOL] Error closing PostgreSQL pool: %s", exc)
                finally:
                    self._pool = None


def configure_sqlite_connection(conn: Any, db_path: str) -> None:
    """Applies per-connection synchronous/timeout pragmas and one-time WAL setup on SQLite."""
    try:
        conn.execute("PRAGMA busy_timeout = 30000;")
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA temp_store = MEMORY;")
    except Exception:
        return

    norm_path = str(db_path or "")
    if not norm_path or norm_path == ":memory:":
        return

    with _WAL_LOCK:
        if norm_path in _WAL_INITIALIZED_PATHS:
            return
        for attempt in range(3):
            try:
                conn.execute("PRAGMA journal_mode = WAL;")
                _WAL_INITIALIZED_PATHS.add(norm_path)
                break
            except Exception as exc:
                if "locked" in str(exc).lower() and attempt < 2:
                    time.sleep(0.05 * (attempt + 1))
                    continue
                logger.debug("[DB_ENGINE] WAL setup skipped for %s: %s", norm_path, exc)
                break


@contextmanager
def db_transaction(engine: Any, commit: bool = False) -> Generator[Tuple[Any, Any], None, None]:
    """
    Context manager opening a DB connection + cursor, committing on clean exit
    when `commit=True`, rolling back on error, and deterministically closing both.
    """
    if engine is None:
        yield None, None
        return

    is_managed = hasattr(engine, "get_connection")
    conn = engine.get_connection() if is_managed else engine
    if conn is None:
        yield None, None
        return

    cursor = conn.cursor()
    try:
        yield conn, cursor
        if commit and hasattr(conn, "commit"):
            conn.commit()
    except Exception:
        if hasattr(conn, "rollback"):
            try:
                conn.rollback()
            except Exception:
                pass
        raise
    finally:
        if hasattr(cursor, "close"):
            try:
                cursor.close()
            except Exception:
                pass
        if (
            is_managed
            and conn is not engine
            and getattr(engine, "is_shared_connection", False) is not True
            and hasattr(conn, "close")
        ):
            try:
                conn.close()
            except Exception:
                pass
