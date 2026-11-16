# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Inter-process advisory file lock serializing heavy GGUF SLM loads across CARINA workers."""

import os
import threading
from contextlib import contextmanager
from typing import Iterator

try:
    import fcntl
except ImportError:  # pragma: no cover - non-POSIX fallback
    fcntl = None  # type: ignore[assignment]

_THREAD_LOCK = threading.RLock()
_THREAD_STATE = threading.local()


def _resolve_lock_path() -> str:
    try:
        from utils.paths import get_base_output_dir

        base = get_base_output_dir()
    except Exception:
        base = os.path.join(os.getcwd(), "tmp")
    lock_dir = os.path.join(base, "locks")
    os.makedirs(lock_dir, exist_ok=True)
    return os.path.join(lock_dir, "slm_gguf.lock")


@contextmanager
def slm_process_lock() -> Iterator[None]:
    """
    Serializes GGUF model loading and inference across `XAI_Worker`, `MFD_Worker`,
    and `AnalysisService` processes so two 2B GGUF models never compete for VRAM/RAM.
    Reentrant within the acquiring thread.
    """
    with _THREAD_LOCK:
        depth = getattr(_THREAD_STATE, "depth", 0)
        lock_file = None
        if depth == 0 and fcntl is not None:
            try:
                lock_file = open(_resolve_lock_path(), "a+")
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            except Exception:
                if lock_file is not None:
                    try:
                        lock_file.close()
                    except Exception:
                        pass
                    lock_file = None
        _THREAD_STATE.depth = depth + 1
        try:
            yield
        finally:
            _THREAD_STATE.depth = depth
            if lock_file is not None:
                try:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                except Exception:
                    pass
                try:
                    lock_file.close()
                except Exception:
                    pass
