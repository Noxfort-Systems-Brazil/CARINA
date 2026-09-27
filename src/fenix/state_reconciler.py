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

# File: src/fenix/state_reconciler.py
# Author: Gabriel Moraes
# Date: September 25, 2026

"""
State Reconciler for CARINA F.E.N.I.X. (Option B - Clean Boundary Handover).

Enforces the industry-standard traffic engineering safety rule:
- When resurrecting after a failure, the AI does NOT command intersections mid-stage.
- The AI discovers the active field stage (e.g. Stage 5) and freezes inference for that intersection.
- The AI runs in 'Shadow Mode' (observing incoming telemetry, warming up TCN/PAE tensors).
- As soon as the field hardware signals that Stage 5 has finished and transitioned to the NEXT stage,
  the AI unfreezes and assumes adaptive control from second zero of the new stage.
"""

import logging
import threading
from dataclasses import dataclass
from typing import Any, Dict, Optional

from src.fenix.protocols import IStateReconciler

logger = logging.getLogger("FenixStateReconciler")


@dataclass
class IntersectionSyncState:
    """Tracking structure for an individual intersection during recovery."""

    tls_id: str
    target_sync_stage: int
    current_stage: int
    is_unfrozen: bool = False
    transitions_seen: int = 0


class StateReconciler(IStateReconciler):
    """
    Manages state reconciliation and handover gating for all intersections.
    Thread-safe.
    """

    def __init__(self):
        self._intersections: Dict[str, IntersectionSyncState] = {}
        self._lock = threading.Lock()

    def reconcile_with_field(self, stages: Dict[str, int]) -> None:
        """
        Registers current field stages for tracked intersections and locks inference.

        Args:
            stages: Mapping of tls_id -> current active stage in field hardware.
        """
        with self._lock:
            self._intersections.clear()
            for tls_id, stage in stages.items():
                self._intersections[tls_id] = IntersectionSyncState(
                    tls_id=tls_id,
                    target_sync_stage=stage,
                    current_stage=stage,
                    is_unfrozen=False,
                    transitions_seen=0,
                )
                logger.info(
                    f"[STATE RECONCILER] 🔒 Synchronized {tls_id} at Stage {stage}. "
                    "Inference FROZEN — waiting for clean stage transition (Option B)."
                )

    def on_stage_transition_detected(self, tls_id: str, new_stage: int) -> bool:
        """
        Notified when field hardware reports or undergoes a stage transition.

        Args:
            tls_id: Intersection identifier.
            new_stage: New active stage reported by field hardware.

        Returns:
            bool: True if this transition resulted in handover (unfreezing) for tls_id.
        """
        with self._lock:
            if tls_id not in self._intersections:
                return False

            state = self._intersections[tls_id]
            old_stage = state.current_stage
            state.current_stage = new_stage

            if new_stage != old_stage:
                state.transitions_seen += 1

            # Option B Gate: Did we transition past the initial sync target stage?
            if not state.is_unfrozen and new_stage != state.target_sync_stage:
                state.is_unfrozen = True
                logger.info(
                    f"[STATE RECONCILER] 🚦 HANDOVER COMPLETE for {tls_id}! "
                    f"Transitioned from sync stage {state.target_sync_stage} -> {new_stage}. "
                    "Adaptive Neural Control UNLOCKED."
                )
                return True

            return False

    def is_inference_allowed(self, tls_id: str) -> bool:
        """
        Checks whether adaptive neural control commands are permitted for tls_id.

        Args:
            tls_id: Intersection identifier.

        Returns:
            bool: True if allowed to actuate, False if still frozen in shadow mode.
        """
        with self._lock:
            if tls_id not in self._intersections:
                # If not tracked by reconciler, default to allowed (normal operation)
                return True
            return self._intersections[tls_id].is_unfrozen

    def get_current_stage(self, tls_id: str) -> Optional[int]:
        """Returns the current known stage for the intersection."""
        with self._lock:
            state = self._intersections.get(tls_id)
            return state.current_stage if state else None

    def is_all_unfrozen(self) -> bool:
        """Returns True if all registered intersections have completed clean handover."""
        with self._lock:
            if not self._intersections:
                return True
            return all(state.is_unfrozen for state in self._intersections.values())

    def get_status_summary(self) -> Dict[str, Any]:
        """Returns structured status of all tracked intersections."""
        with self._lock:
            return {
                tls_id: {
                    "target_sync_stage": state.target_sync_stage,
                    "current_stage": state.current_stage,
                    "is_unfrozen": state.is_unfrozen,
                    "transitions_seen": state.transitions_seen,
                }
                for tls_id, state in self._intersections.items()
            }

    def reset(self) -> None:
        """Clears all reconciliation state."""
        with self._lock:
            self._intersections.clear()
            logger.info("[STATE RECONCILER] Reconciler state reset.")
