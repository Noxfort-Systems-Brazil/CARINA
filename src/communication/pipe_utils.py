# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Thread-safe multiprocessing pipe wrapper serializing concurrent `.send()` calls."""

import threading
from typing import Any


class ThreadSafePipeConnection:
    """
    Serializes concurrent `.send()` calls across HFT worker, event-loop, and gateway threads
    while keeping `.poll()` and `.recv()` lock-free for duplex reads.
    """

    def __init__(self, conn: Any) -> None:
        self._conn = conn
        self._send_lock = threading.Lock()

    def send(self, obj: Any) -> None:
        with self._send_lock:
            self._conn.send(obj)

    def send_bytes(self, *args: Any, **kwargs: Any) -> None:
        with self._send_lock:
            self._conn.send_bytes(*args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._conn, name)


def wrap_thread_safe_pipe(conn: Any) -> Any:
    """Wraps a real Connection in `ThreadSafePipeConnection`, leaving None and test mocks unwrapped."""
    if conn is None or isinstance(conn, ThreadSafePipeConnection) or hasattr(conn, "assert_called"):
        return conn
    return ThreadSafePipeConnection(conn)
