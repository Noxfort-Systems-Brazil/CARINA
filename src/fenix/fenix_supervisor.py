# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
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
# along with this program. If not, see <https://www.gnu.org/licenses/>.

# File: src/fenix/fenix_supervisor.py
# Author: Gabriel Moraes
# Date: September 25, 2026

"""
F.E.N.I.X. Process Supervisor & Orchestrator Facade (SOLID Architecture).

Responsible for:
- Coordinating out-of-process lifecycle states of the AI neural engine.
- Enforcing crash recovery policies and anti-loop backoffs.
- Resurrecting dead/frozen processes and initiating the FROZEN_SYNC state.
- Invocable by CARINA's Watchdog upon detected failures.
"""

import logging
import os
import sys
import threading
import time
from typing import Callable, Dict, List, Optional

from src.fenix.process_runner import SubprocessRunner
from src.fenix.protocols import FenixState, IProcessRunner, IProcessSupervisor, IRecoveryPolicy
from src.fenix.recovery_policy import WindowedCrashRecoveryPolicy

logger = logging.getLogger("FenixSupervisor")


class FenixSupervisor(IProcessSupervisor):
    """
    Guardian supervisor orchestrating AI Process resurrection and lifecycle safety.
    """

    def __init__(
        self,
        runner: Optional[IProcessRunner] = None,
        recovery_policy: Optional[IRecoveryPolicy] = None,
        default_command: Optional[List[str]] = None,
        on_status_changed: Optional[Callable[[FenixState, str], None]] = None,
    ):
        self.runner = runner or SubprocessRunner()
        self.recovery_policy = recovery_policy or WindowedCrashRecoveryPolicy()
        self.default_command = default_command or [sys.executable, "-m", "src.main"]
        self.on_status_changed = on_status_changed

        self._state = FenixState.IDLE
        self._lock = threading.Lock()

    @property
    def state(self) -> FenixState:
        """Returns current F.E.N.I.X. lifecycle state."""
        with self._lock:
            return self._state

    @property
    def child_pid(self) -> Optional[int]:
        """Returns PID of supervised child process or None."""
        return self.runner.pid

    @property
    def is_child_alive(self) -> bool:
        """Returns True if supervised child process is currently alive."""
        return self.runner.is_alive

    def _set_state(self, new_state: FenixState, message: str = ""):
        """Updates internal state and notifies registered listeners."""
        self._state = new_state
        logger.info(f"[FENIX SUPERVISOR] State: {new_state.value} | {message}")
        if self.on_status_changed:
            try:
                self.on_status_changed(new_state, message)
            except Exception as e:
                logger.error(f"[FENIX SUPERVISOR] Error in on_status_changed callback: {e}")

    def resurrect_ai(self, custom_command: Optional[List[str]] = None) -> bool:
        """
        Executes safe resurrection of the AI engine:
        1. Checks anti-loop crash limits via recovery policy.
        2. Terminates old/zombie process instances with SIGKILL fallback.
        3. Applies backoff sleep.
        4. Spawns new process configured in FROZEN_SYNC mode.

        Args:
            custom_command: Optional custom command list to execute instead of default.

        Returns:
            bool: True if process was successfully resurrected, False if halted/failed.
        """
        with self._lock:
            if not self.recovery_policy.should_restart():
                self._set_state(
                    FenixState.HALTED,
                    f"Crash limit exceeded ({self.recovery_policy.crash_count} crashes). "
                    "Halting resurrection to protect system. Maintaining FAILSAFE fixed plans.",
                )
                return False

            self._set_state(FenixState.RESTARTING, "Resurrecting AI Engine...")

            # 1. Terminate old instance if still lingering or dead
            if self.runner.is_alive:
                logger.info("[FENIX SUPERVISOR] Terminating stalled child process...")
                self.runner.terminate(timeout_seconds=2.0)

            # 2. Backoff delay
            backoff = self.recovery_policy.get_backoff_seconds()
            if backoff > 0:
                logger.info(f"[FENIX SUPERVISOR] Applying recovery backoff: {backoff:.2f}s")
                time.sleep(backoff)

            # 3. Build command and execution environment
            cmd = custom_command or self.default_command
            env = os.environ.copy()
            env["CARINA_SUPERVISED"] = "1"
            env["CARINA_RECONCILE"] = "1"
            env["PYTHONUNBUFFERED"] = "1"

            # 4. Spawn child process
            success = self.runner.spawn(cmd, env=env)
            if success:
                self._set_state(
                    FenixState.FROZEN_SYNC, f"AI Engine resurrected [PID: {self.runner.pid}] in FROZEN_SYNC mode."
                )
                return True
            else:
                self._set_state(FenixState.HALTED, "Failed to spawn resurrected AI Engine.")
                return False

    def record_child_crash(self, exit_code: int) -> None:
        """
        Records a child process crash and notifies the recovery policy.

        Args:
            exit_code: Exit status code of crashed process.
        """
        with self._lock:
            self.recovery_policy.record_crash(exit_code)
            self._set_state(FenixState.FAILSAFE_ACTIVE, f"Child process crashed with exit code {exit_code}.")

    def confirm_handover_complete(self) -> None:
        """Called once Option B clean handover is achieved to return to NORMAL state."""
        with self._lock:
            self._set_state(FenixState.NORMAL, "State reconciliation and handover complete.")

    def stop(self, timeout_seconds: float = 5.0) -> None:
        """Gracefully terminates the supervised AI process."""
        with self._lock:
            if self.runner.is_alive:
                self.runner.terminate(timeout_seconds=timeout_seconds)
            self._set_state(FenixState.IDLE, "Supervisor stopped.")
