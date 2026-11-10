# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Lockdown Enforcer (Clean Architecture / SOLID: SRP).
Encapsulates rate limiting, lockdown state evaluation, and attempt threshold tracking.
"""

import logging
from typing import Any, Callable, Optional

from src.security.events import LockdownTriggeredEvent, SecurityEvent

logger = logging.getLogger("LockdownEnforcer")


class LockdownEnforcer:
    """
    Domain/Application component responsible for evaluating lockdown states
    and tracking failed attempt thresholds across repositories and lockdown managers.
    """

    def __init__(
        self,
        lockdown_manager: Any = None,
        user_repository: Any = None,
        config: Optional[Any] = None,
        event_dispatcher: Optional[Callable[[SecurityEvent], None]] = None,
    ):
        self.lockdown_manager = lockdown_manager
        self.user_repository = user_repository
        self.config = config
        self.event_dispatcher = event_dispatcher

    def is_lockdown(self) -> bool:
        """Returns True if the system is currently in lockdown state."""
        if hasattr(self.lockdown_manager, "is_lockdown"):
            return self.lockdown_manager.is_lockdown()
        elif hasattr(self.lockdown_manager, "is_active"):
            return self.lockdown_manager.is_active()
        return False

    def clear_lockdown(self) -> None:
        """Removes the lockdown state and resets failed attempt counters."""
        if hasattr(self.lockdown_manager, "clear_lockdown"):
            self.lockdown_manager.clear_lockdown()
        elif hasattr(self.lockdown_manager, "clear"):
            self.lockdown_manager.clear()
        if hasattr(self.user_repository, "reset_failed_attempts"):
            self.user_repository.reset_failed_attempts()

    def reset_attempts(self) -> None:
        """Resets failed attempt counters without altering lockdown lock status."""
        if hasattr(self.lockdown_manager, "reset_attempts"):
            self.lockdown_manager.reset_attempts()
        if hasattr(self.user_repository, "reset_failed_attempts"):
            self.user_repository.reset_failed_attempts()

    def record_failed_attempt(self) -> bool:
        """
        Increments failed attempt counters and triggers lockdown if threshold is met.
        Returns True if lockdown is active or was triggered during this call.
        """
        if self.is_lockdown():
            return True

        if getattr(self.lockdown_manager, "_explicit_max", False):
            max_attempts = getattr(self.lockdown_manager, "max_failed_attempts", None)
        else:
            max_attempts = getattr(self.config, "max_failed_attempts", None) if self.config else None
            if max_attempts is None:
                max_attempts = getattr(self.lockdown_manager, "max_failed_attempts", 3)
        if max_attempts is None:
            max_attempts = 3

        new_count = 0
        if hasattr(self.user_repository, "increment_failed_attempts"):
            new_count = self.user_repository.increment_failed_attempts()

        lm_locked = False
        if hasattr(self.lockdown_manager, "record_failed_attempt"):
            lm_locked = bool(self.lockdown_manager.record_failed_attempt())

        if lm_locked or (new_count and new_count >= max_attempts):
            if hasattr(self.lockdown_manager, "trigger_lockdown"):
                self.lockdown_manager.trigger_lockdown()
            elif hasattr(self.lockdown_manager, "activate"):
                self.lockdown_manager.activate()

            if self.event_dispatcher:
                try:
                    self.event_dispatcher(
                        LockdownTriggeredEvent(
                            failed_attempts=new_count or max_attempts,
                            reason="Exceeded maximum failed attempts threshold",
                        )
                    )
                except Exception as e:
                    logger.debug(f"[LockdownEnforcer] Event dispatch failed: {e}")
            return True

        return False
