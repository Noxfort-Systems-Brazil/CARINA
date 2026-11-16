# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Transactional Database Executor for the EVP subsystem (DIP / Clean Architecture).
Encapsulates connection lifecycle, cursors, and commits for PostgreSQL and SQLite.
"""

import logging
import queue
import threading
from contextlib import contextmanager
from typing import Any, Callable, Generator, List, Optional

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


class AsyncTelemetryPersistQueue:
    """Bounded latest-wins background writer batching EVP telemetry inserts off the GPS loop."""

    def __init__(self, batch_fn: Callable[[List[Any]], Any], maxsize: int = 512, max_batch: int = 64):
        self._batch_fn = batch_fn
        self._max_batch = max(1, int(max_batch))
        self._queue: queue.Queue = queue.Queue(maxsize=max(16, int(maxsize)))
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stopped = False

    def enqueue(self, snapshot: Any) -> None:
        with self._lock:
            if self._stopped:
                return
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(
                    target=self._run,
                    daemon=True,
                    name="EVP-TelemetryWriter",
                )
                self._thread.start()
        if self._queue.full():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                pass
        try:
            self._queue.put_nowait(snapshot)
        except queue.Full:
            pass

    def _run(self) -> None:
        while not self._stopped:
            first = self._queue.get()
            if first is None:
                break
            batch = [first]
            while len(batch) < self._max_batch:
                try:
                    nxt = self._queue.get_nowait()
                except queue.Empty:
                    break
                if nxt is None:
                    self._stopped = True
                    break
                batch.append(nxt)
            try:
                self._batch_fn(batch)
            except Exception as exc:
                logger.error(f"[AsyncTelemetryPersistQueue] Erro no lote de telemetria: {exc}", exc_info=True)

    def stop(self) -> None:
        with self._lock:
            self._stopped = True
            t = self._thread
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass
        if t is not None and t.is_alive():
            t.join(timeout=1.0)
