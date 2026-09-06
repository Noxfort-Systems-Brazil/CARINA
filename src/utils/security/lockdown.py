# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: src/utils/security/lockdown.py
# Author: Gabriel Moraes
# Date: September 05, 2026

import logging
import os
from typing import Optional

from src.utils.security.interfaces import ILockdownManager


class FileLockdownManager(ILockdownManager):
    """
    Manages the persistent system lockdown flag on the filesystem.
    """

    def __init__(self, lockdown_file: str, locale_manager: Optional[object] = None):
        self.lockdown_file = lockdown_file
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

    def is_active(self) -> bool:
        """Returns True if the lockdown flag file exists on disk."""
        return os.path.exists(self.lockdown_file)

    def activate(self) -> None:
        """Creates the persistent lockdown flag file on disk."""
        try:
            os.makedirs(os.path.dirname(self.lockdown_file), exist_ok=True)
            with open(self.lockdown_file, "w", encoding="utf-8") as f:
                f.write("LOCKDOWN_ACTIVE")
            msg = self._get_string(
                "security_manager.lockdown_triggered",
                default="[SecurityManager] 🚨 SYSTEM ENTERED LOCKDOWN (Too many failed attempts).",
            )
            logging.critical(msg)
        except Exception as e:
            err_msg = self._get_string(
                "security_manager.lockdown_flag_error",
                default="[SecurityManager] Failed to create lockdown flag: {error}",
                error=e,
            )
            logging.error(err_msg)

    def clear(self) -> None:
        """Removes the persistent lockdown flag file from disk."""
        if os.path.exists(self.lockdown_file):
            try:
                os.remove(self.lockdown_file)
            except Exception as e:
                err_msg = self._get_string(
                    "security_manager.lockdown_remove_error",
                    default="[SecurityManager] Failed to remove lockdown flag: {error}",
                    error=e,
                )
                logging.error(err_msg)


class InMemoryLockdownManager(ILockdownManager):
    """
    In-memory implementation of ILockdownManager for testing and environments without disk writes.
    """

    def __init__(self, active: bool = False):
        self._active = active

    def is_active(self) -> bool:
        return self._active

    def activate(self) -> None:
        self._active = True

    def clear(self) -> None:
        self._active = False
