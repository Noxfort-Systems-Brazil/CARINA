# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Lockdown & Brute-Force Rate Limiting Manager (SOLID: SRP & DIP).
Provides persistent file-based and volatile in-memory implementations.
"""

import logging
import os
from typing import Any, Callable, Optional

from src.security.interfaces import ILockdownManager

logger = logging.getLogger("LockdownManager")


class FileLockdownManager(ILockdownManager):
    """
    Manages the persistent system lockdown flag on the filesystem and coordinates
    failed attempt counters against a configured threshold.
    """

    def __init__(
        self,
        lockdown_file: str,
        max_failed_attempts: int = 5,
        attempts_getter: Optional[Callable[[], int]] = None,
        attempts_setter: Optional[Callable[[int], None]] = None,
        locale_manager: Optional[object] = None,
        attempt_store: Optional[Any] = None,
        max_attempts: Optional[int] = None,
    ):
        self.lockdown_file = lockdown_file
        self.max_failed_attempts = max_attempts if max_attempts is not None else max_failed_attempts
        if attempt_store is not None:
            self.attempts_getter = getattr(attempt_store, "get_failed_attempts", attempts_getter)
            self.attempts_setter = getattr(attempt_store, "set_failed_attempts", attempts_setter)
        else:
            self.attempts_getter = attempts_getter
            self.attempts_setter = attempts_setter
        self.locale_manager = locale_manager

    def _get_string(self, key: str, default: str = "", **kwargs) -> str:
        if self.locale_manager and hasattr(self.locale_manager, "get_string"):
            try:
                res = self.locale_manager.get_string(key, default=default, **kwargs)
                return res
            except TypeError:
                res = self.locale_manager.get_string(key, default=default)
                if kwargs and isinstance(res, str):
                    try:
                        return res.format(**kwargs)
                    except Exception:
                        pass
                return res
        return default.format(**kwargs) if default and kwargs else (default or key)

    def is_lockdown(self) -> bool:
        """Returns True if the lockdown flag file exists on disk."""
        return os.path.isfile(self.lockdown_file)

    def trigger_lockdown(self) -> None:
        """Creates the persistent lockdown flag file on disk."""
        try:
            os.makedirs(os.path.dirname(self.lockdown_file), exist_ok=True)
            with open(self.lockdown_file, "w", encoding="utf-8") as f:
                f.write("LOCKDOWN_ACTIVE")
            msg = self._get_string(
                "security_manager.lockdown_triggered",
                default="[SecurityManager] 🚨 SYSTEM ENTERED LOCKDOWN (Too many failed attempts).",
            )
            logger.critical(msg)
        except Exception as e:
            err_msg = self._get_string(
                "security_manager.lockdown_flag_error",
                default=f"[SecurityManager] Failed to create lockdown flag: {e}",
                error=e,
            )
            logger.error(err_msg, exc_info=True)

    def clear_lockdown(self) -> None:
        """Removes the persistent lockdown flag file from disk and resets counters."""
        if os.path.exists(self.lockdown_file):
            try:
                os.remove(self.lockdown_file)
            except Exception as e:
                err_msg = self._get_string(
                    "security_manager.lockdown_remove_error",
                    default=f"[SecurityManager] Failed to remove lockdown flag: {e}",
                    error=e,
                )
                logger.error(err_msg, exc_info=True)
        self.reset_attempts()

    def record_failed_attempt(self) -> bool:
        """
        Increments failed login attempts and triggers lockdown if threshold is met.
        Returns True if lockdown is active or was triggered during this call.
        """
        if self.is_lockdown():
            return True

        current = 0
        if self.attempts_getter is not None:
            try:
                current = self.attempts_getter()
            except Exception as e:
                logger.error(f"Error reading failed attempts: {e}", exc_info=True)

        current += 1

        if self.attempts_setter is not None:
            try:
                self.attempts_setter(current)
            except Exception as e:
                logger.error(f"Error persisting failed attempts: {e}", exc_info=True)

        logger.warning(
            self._get_string(
                "security_manager.failed_attempt_registered",
                default=f"[SecurityManager] Failed login attempt recorded. Total: {current}/{self.max_failed_attempts}",
                current=current,
                max=self.max_failed_attempts,
            )
        )

        if current >= self.max_failed_attempts:
            self.trigger_lockdown()
            return True

        return False

    def reset_attempts(self) -> None:
        """Resets the failed attempt counter to 0."""
        if self.attempts_setter is not None:
            try:
                self.attempts_setter(0)
            except Exception as e:
                logger.error(f"Error resetting failed attempts: {e}", exc_info=True)

    # --- Backward compatibility aliases ---
    def is_active(self) -> bool:
        return self.is_lockdown()

    def activate(self) -> None:
        self.trigger_lockdown()

    def clear(self) -> None:
        self.clear_lockdown()


class InMemoryLockdownManager(ILockdownManager):
    """
    In-memory implementation of ILockdownManager for testing and volatile execution.
    """

    def __init__(self, active: bool = False, max_failed_attempts: Optional[int] = None):
        self._active = active
        self._explicit_max = max_failed_attempts is not None
        self.max_failed_attempts = max_failed_attempts if max_failed_attempts is not None else 5
        self.failed_attempts = 0

    def is_lockdown(self) -> bool:
        return self._active

    def trigger_lockdown(self) -> None:
        self._active = True

    def clear_lockdown(self) -> None:
        self._active = False
        self.failed_attempts = 0

    def record_failed_attempt(self) -> bool:
        if self._active:
            return True
        self.failed_attempts += 1
        if self.failed_attempts >= self.max_failed_attempts:
            self._active = True
            return True
        return False

    def reset_attempts(self) -> None:
        self.failed_attempts = 0

    # --- Backward compatibility aliases ---
    def is_active(self) -> bool:
        return self.is_lockdown()

    def activate(self) -> None:
        self.trigger_lockdown()

    def clear(self) -> None:
        self.clear_lockdown()
