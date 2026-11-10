# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Rate-Limiting Failed Attempt Storage Components (SOLID: SRP & ISP).
Segregates failed login attempt tracking from user account repositories.
"""

import json
import logging
import os
from typing import Any, Dict

from src.security.interfaces import IAttemptCounterStore

logger = logging.getLogger("AttemptStore")


class JsonAttemptStore(IAttemptCounterStore):
    """
    Persists failed authentication attempts to a JSON file (e.g. security.json).
    """

    def __init__(self, security_file: str):
        self.security_file = security_file

    def _read_data(self) -> Dict[str, Any]:
        if not os.path.exists(self.security_file):
            return {}
        try:
            with open(self.security_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.debug(f"Failed to read attempt count from {self.security_file}: {e}")
            return {}

    def _write_data(self, data: Dict[str, Any]) -> None:
        try:
            os.makedirs(os.path.dirname(self.security_file), exist_ok=True)
            with open(self.security_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to write attempt count to {self.security_file}: {e}", exc_info=True)

    def get_failed_attempts(self) -> int:
        """Returns the recorded count of failed authentication attempts."""
        data = self._read_data()
        return int(data.get("failed_attempts", 0))

    def set_failed_attempts(self, count: int) -> None:
        """Persists the updated count of failed authentication attempts."""
        data = self._read_data()
        data["failed_attempts"] = max(0, count)
        self._write_data(data)


class MemoryAttemptStore(IAttemptCounterStore):
    """
    Volatile in-memory counter store for tests and ephemeral environments.
    """

    def __init__(self, initial_count: int = 0):
        self._count = max(0, initial_count)

    def get_failed_attempts(self) -> int:
        return self._count

    def set_failed_attempts(self, count: int) -> None:
        self._count = max(0, count)
