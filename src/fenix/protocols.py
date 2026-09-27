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

# File: src/fenix/protocols.py
# Author: Gabriel Moraes
# Date: September 25, 2026

"""
Protocols and interfaces for CARINA F.E.N.I.X. (Self-Healing & Auto-Resurrection).

Adheres strictly to SOLID:
- [SRP] Clear separation of contracts: process execution, recovery policy, state reconciliation.
- [ISP] Small, dedicated protocols for each responsibility.
- [DIP] All orchestrators depend on these protocols rather than concrete classes.
"""

from enum import Enum
from typing import Dict, List, Optional, Protocol, runtime_checkable


class FenixState(Enum):
    """Lifecycle states of the F.E.N.I.X. supervisor and AI process."""

    IDLE = "IDLE"
    FAILSAFE_ACTIVE = "FAILSAFE_ACTIVE"
    RESTARTING = "RESTARTING"
    FROZEN_SYNC = "FROZEN_SYNC"
    SHADOW_WARMUP = "SHADOW_WARMUP"
    HANDOVER_PENDING = "HANDOVER_PENDING"
    NORMAL = "NORMAL"
    HALTED = "HALTED"


@runtime_checkable
class IRecoveryPolicy(Protocol):
    """Protocol for crash recovery rules, backoff calculations, and restart limits."""

    def record_crash(self, exit_code: int) -> None:
        """Records a process crash occurrence."""
        ...

    def should_restart(self) -> bool:
        """Evaluates whether the process is allowed to be restarted or halted."""
        ...

    def get_backoff_seconds(self) -> float:
        """Returns the backoff duration in seconds before attempting resurrection."""
        ...

    def reset(self) -> None:
        """Resets the crash history and recovery state."""
        ...

    @property
    def crash_count(self) -> int:
        """Returns the number of active crashes within the current sliding window."""
        ...


@runtime_checkable
class IProcessRunner(Protocol):
    """Protocol for low-level OS process management and execution."""

    def spawn(self, command: List[str], env: Optional[Dict[str, str]] = None) -> bool:
        """Spawns an OS subprocess."""
        ...

    def terminate(self, timeout_seconds: float = 5.0) -> None:
        """Gracefully terminates the subprocess (SIGTERM -> SIGKILL if timed out)."""
        ...

    def poll(self) -> Optional[int]:
        """Returns the process exit code if terminated, or None if still running."""
        ...

    @property
    def pid(self) -> Optional[int]:
        """Returns the process PID or None if not running."""
        ...

    @property
    def is_alive(self) -> bool:
        """Checks if the subprocess is currently running."""
        ...


@runtime_checkable
class IStateReconciler(Protocol):
    """
    Protocol for Option B State Reconciliation and Clean Boundary Handover.
    Ensures AI never commands an intersection mid-stage; instead, waits for
    the local controller's next stage transition before taking over.
    """

    def reconcile_with_field(self, stages: Dict[str, int]) -> None:
        """Synchronizes tracked intersections with current field stages in FROZEN_SYNC mode."""
        ...

    def is_inference_allowed(self, tls_id: str) -> bool:
        """Returns True only if the specified intersection has completed handover."""
        ...

    def on_stage_transition_detected(self, tls_id: str, new_stage: int) -> bool:
        """
        Notified when a stage change occurs in field hardware.
        If this transition moves past the initial sync stage, unlocks inference (handover).
        Returns True if this transition resulted in handover for tls_id.
        """
        ...

    def get_current_stage(self, tls_id: str) -> Optional[int]:
        """Returns the current tracked stage for the intersection, or None."""
        ...

    def is_all_unfrozen(self) -> bool:
        """Returns True if all registered intersections have completed handover."""
        ...

    def reset(self) -> None:
        """Resets reconciliation state."""
        ...


@runtime_checkable
class IProcessSupervisor(Protocol):
    """High-level facade orchestrator protocol for F.E.N.I.X."""

    def resurrect_ai(self, custom_command: Optional[List[str]] = None) -> bool:
        """Terminates zombie instance, evaluates recovery policy, and respawns AI process."""
        ...

    def stop(self, timeout_seconds: float = 5.0) -> None:
        """Stops the supervised process cleanly."""
        ...

    @property
    def state(self) -> FenixState:
        """Returns current F.E.N.I.X. lifecycle state."""
        ...
