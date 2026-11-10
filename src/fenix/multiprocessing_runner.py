# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Multiprocessing Process Runner implementation for CARINA F.E.N.I.X. (SOLID Architecture).
Adapts Python multiprocessing.Process to IProcessRunner protocol.
"""

import logging
import multiprocessing
import os
import threading
from typing import Callable, Dict, List, Optional, Tuple

from src.fenix.protocols import IProcessRunner

logger = logging.getLogger("FenixMultiprocessingRunner")


class MultiprocessingProcessRunner(IProcessRunner):
    """
    Adapter implementing IProcessRunner for Python multiprocessing.Process instances.
    Enables FenixSupervisor to supervise spawned multiprocess workers.
    """

    def __init__(
        self,
        target: Optional[Callable] = None,
        args: Tuple = (),
        name: str = "AI_Process",
        process: Optional[multiprocessing.Process] = None,
    ):
        self.target = target
        self.args = args
        self.name = name
        self._process = process
        self._lock = threading.Lock()

    @property
    def pid(self) -> Optional[int]:
        with self._lock:
            if self._process is not None:
                return self._process.pid
            return None

    @property
    def is_alive(self) -> bool:
        with self._lock:
            if self._process is None:
                return False
            return self._process.is_alive()

    def poll(self) -> Optional[int]:
        """Returns the process exit code if terminated, or None if still running."""
        with self._lock:
            if self._process is None:
                return None
            return self._process.exitcode

    def set_process(self, process: multiprocessing.Process) -> None:
        """Sets an already running or newly instantiated multiprocessing.Process."""
        with self._lock:
            self._process = process

    def spawn(self, command: Optional[List[str]] = None, env: Optional[Dict[str, str]] = None) -> bool:
        """Spawns a new multiprocessing.Process using the configured target and args."""
        with self._lock:
            if self.target is None:
                logger.error("[MultiprocessingProcessRunner] Cannot spawn: no target function configured.")
                return False
            try:
                if env:
                    os.environ.update(env)
                logger.info(f"[MultiprocessingProcessRunner] Spawning supervised process [{self.name}]...")
                self._process = multiprocessing.Process(target=self.target, args=self.args, name=self.name)
                self._process.start()
                logger.info(f"[MultiprocessingProcessRunner] Process [{self.name}] spawned with PID: {self._process.pid}")
                return True
            except Exception as e:
                logger.error(f"[MultiprocessingProcessRunner] Error spawning process [{self.name}]: {e}", exc_info=True)
                return False

    def terminate(self, timeout_seconds: float = 3.0, timeout_sec: Optional[float] = None) -> bool:
        """Terminates supervised multiprocessing process with join timeout and kill fallback."""
        effective_timeout = timeout_sec if timeout_sec is not None else timeout_seconds
        with self._lock:
            if self._process is None or not self._process.is_alive():
                return True
            try:
                self._process.terminate()
                self._process.join(timeout=effective_timeout)
                if self._process.is_alive():
                    self._process.kill()
                    self._process.join(timeout=1.0)
                return True
            except Exception as e:
                logger.error(f"[MultiprocessingProcessRunner] Error terminating process [{self.name}]: {e}", exc_info=True)
                return False

    def kill(self) -> bool:
        """Immediately sends kill signal to supervised process."""
        with self._lock:
            if self._process is None or not self._process.is_alive():
                return True
            try:
                self._process.kill()
                self._process.join(timeout=1.0)
                return True
            except Exception as e:
                logger.error(f"[MultiprocessingProcessRunner] Error killing process [{self.name}]: {e}", exc_info=True)
                return False
