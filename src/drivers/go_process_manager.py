# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# File: src/drivers/go_process_manager.py
# Author: Gabriel Moraes
# Date: 2026-09-25

"""
Manages the lifecycle, subprocess execution, and standard error streams of the carina-go binary.
Isolated responsibility according to the Single Responsibility Principle (SRP).
"""

import atexit
import logging
import os
import subprocess
import threading
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class GoProcessManager:
    """
    Supervises the Go hardware gateway subprocess execution, shutdown and logging.
    """

    def __init__(self, binary_path: str) -> None:
        self.binary_path = binary_path
        self.process: Optional[subprocess.Popen] = None
        self._running = False
        self._stderr_thread: Optional[threading.Thread] = None
        atexit.register(self.stop)

    def is_running(self) -> bool:
        """Checks if subprocess is alive."""
        return self._running and self.process is not None and self.process.poll() is None

    def start(self) -> bool:
        """Spawns the Go binary and starts the stderr logger thread."""
        if self.is_running():
            return True

        if not os.path.exists(self.binary_path):
            logger.error(f"[GoProcessManager] Gateway binary not found at: {self.binary_path}")
            return False

        try:
            logger.info(f"[GoProcessManager] Spawning Go Hardware Gateway: {self.binary_path}")
            self.process = subprocess.Popen(
                [self.binary_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line-buffered
                close_fds=True,
            )
            self._running = True

            self._stderr_thread = threading.Thread(
                target=self._read_stderr_loop,
                daemon=True,
                name="GoGatewayStderrReader",
            )
            self._stderr_thread.start()
            return True

        except Exception as e:
            logger.error(f"[GoProcessManager] Failed to start Go binary: {e}")
            self.stop()
            return False

    def stop(self, pre_stop_hook: Optional[Callable[[], None]] = None) -> None:
        """Performs graceful shutdown of the Go gateway process and cleans up resources."""
        if not self._running:
            return

        self._running = False
        logger.info("[GoProcessManager] Stopping Go Hardware Gateway process...")

        try:
            if pre_stop_hook:
                try:
                    pre_stop_hook()
                except Exception as hook_err:
                    logger.debug(f"[GoProcessManager] Error running pre-stop hook: {hook_err}")

            if self.process and self.process.poll() is None:
                if self.process.stdin:
                    try:
                        self.process.stdin.close()
                    except Exception:
                        pass

                self.process.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            logger.warning("[GoProcessManager] Process did not terminate within timeout; killing...")
            if self.process:
                self.process.kill()
        except Exception as e:
            logger.error(f"[GoProcessManager] Error during gateway termination: {e}")
        finally:
            self.process = None

    def _read_stderr_loop(self) -> None:
        """Reads log lines from the Go gateway's stderr and routes them to Python logger."""
        while self._running and self.process and self.process.stderr:
            try:
                line = self.process.stderr.readline()
                if not line:
                    break
                line_str = line.strip()
                if line_str:
                    logger.info(f"[GoGateway] {line_str}")
            except Exception:
                break
