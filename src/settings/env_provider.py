# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# File: src/settings/env_provider.py
# Author: Gabriel Moraes
# Date: 2026-09-12

"""
Handles 12-Factor App secret injection and .env file synchronization.
Complies with Single Responsibility Principle (SRP).
"""

import logging
import os
import threading
from typing import Dict, Optional

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

try:
    from settings.interfaces import IEnvironmentProvider
except ImportError:
    from src.settings.interfaces import IEnvironmentProvider


class DotenvSecretProvider(IEnvironmentProvider):
    """Manages environment variable overrides and .env synchronization for sensitive secrets."""

    DEFAULT_ENV_TO_SETTINGS_MAP: Dict[str, str] = {
        "CARINA_DB_USER": "db_user",
        "CARINA_DB_PASSWORD": "db_password",
        "CARINA_DB_HOST": "db_host",
        "CARINA_DB_PORT": "db_port",
        "CARINA_DB_NAME": "db_name",
        "CARINA_DB_SCHEMA": "db_schema",
        "CARINA_SNMP_COMMUNITY": "snmp_community_string",
        "CARINA_MQTT_HOST": "monitor_mqtt_host",
        "CARINA_MQTT_PORT": "monitor_mqtt_port",
    }

    SETTINGS_TO_ENV_MAP: Dict[str, str] = {v: k for k, v in DEFAULT_ENV_TO_SETTINGS_MAP.items()}

    _lock = threading.Lock()

    def __init__(self, env_path: Optional[str] = None):
        if env_path:
            self._env_path = env_path
        else:
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            self._env_path = os.path.join(project_root, ".env")

    @property
    def env_path(self) -> str:
        return self._env_path

    def has_env_file(self) -> bool:
        return os.path.isfile(self._env_path)

    def load_env(self) -> None:
        """Loads .env variables into os.environ using python-dotenv or fallback manual parsing."""
        if load_dotenv is not None:
            load_dotenv(self._env_path)

        if self.has_env_file():
            try:
                with open(self._env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k and k not in os.environ:
                            os.environ[k] = v
            except Exception as e:
                logging.warning(f"[DotenvSecretProvider] Failed manual parse of .env: {e}")

    def get_overrides(self) -> Dict[str, str]:
        """Returns setting_key -> env_value for all mapped environment variables that are set."""
        self.load_env()
        overrides: Dict[str, str] = {}
        for env_key, settings_key in self.DEFAULT_ENV_TO_SETTINGS_MAP.items():
            env_val = os.getenv(env_key)
            if env_val is not None and env_val != "":
                overrides[settings_key] = env_val
        return overrides

    def sync_variable(self, env_key: str, value: str) -> bool:
        """
        Updates in-memory os.environ and updates or appends the key in .env file safely.
        Thread-safe execution via Lock.
        """
        os.environ[env_key] = str(value)
        if not self.has_env_file():
            return True

        with self._lock:
            try:
                with open(self._env_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                updated = False
                new_lines = []
                for line in lines:
                    if line.strip().startswith(f"{env_key}="):
                        new_lines.append(f"{env_key}={value}\n")
                        updated = True
                    else:
                        new_lines.append(line)

                if not updated:
                    new_lines.append(f"\n{env_key}={value}\n")

                with open(self._env_path, "w", encoding="utf-8") as f:
                    f.writelines(new_lines)
                return True
            except Exception as err:
                logging.warning(f"[DotenvSecretProvider] Failed to update {env_key} in .env: {err}")
                return False
