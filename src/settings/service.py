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

# File: src/settings/service.py
# Author: Gabriel Moraes
# Date: 2026-09-12

"""
High-level settings orchestrator service implementing ISettingsReader and ISettingsWriter.
Complies with Dependency Inversion Principle (DIP) and Single Responsibility Principle (SRP).
"""

import configparser
import logging
import os
from typing import Any, Dict, Optional

try:
    from settings.env_provider import DotenvSecretProvider
    from settings.ini_storage import IniFileStorage
    from settings.interfaces import IEnvironmentProvider, ISettingsReader, ISettingsStorage, ISettingsWriter
    from settings.schema import SettingsSchema
except ImportError:
    from src.settings.env_provider import DotenvSecretProvider
    from src.settings.ini_storage import IniFileStorage
    from src.settings.interfaces import IEnvironmentProvider, ISettingsReader, ISettingsStorage, ISettingsWriter
    from src.settings.schema import SettingsSchema


class SettingsService(ISettingsReader, ISettingsWriter):
    """
    Coordinates reading, writing, and environment overrides of configuration settings.
    Receives persistence and environment abstractions via dependency injection.
    """

    def __init__(
        self,
        storage: Optional[ISettingsStorage] = None,
        env_provider: Optional[IEnvironmentProvider] = None,
        schema: Optional[SettingsSchema] = None,
        locale_manager: Optional[Any] = None,
    ):
        self.storage = storage or IniFileStorage()
        self.env_provider = env_provider or DotenvSecretProvider()
        self.schema = schema or SettingsSchema()
        self.locale_manager = locale_manager

        log_msg = self._get_string(
            "settings_manager.init",
            default="[SettingsService] Settings service pointing to: {path}",
            path=self.storage.storage_path,
        )
        logging.debug(log_msg)

    def _get_string(self, key: str, default: str = None, **kwargs) -> str:
        if self.locale_manager and hasattr(self.locale_manager, "get_string"):
            return self.locale_manager.get_string(key, default=default, **kwargs)
        return default.format(**kwargs) if default and kwargs else (default or key)

    def load_config(self) -> configparser.ConfigParser:
        """Reads and returns the low-level ConfigParser instance from storage."""
        return self.storage.read_config()

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieves a single configuration value by key."""
        settings = self.load_settings()
        return settings.get(key, default)

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Retrieves a configuration value coerced to boolean."""
        val = self.get(key, default)
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.strip().lower() in ("true", "1", "yes", "on")
        return bool(val)

    def get_int(self, key: str, default: int = 0) -> int:
        """Retrieves a configuration value coerced to integer."""
        val = self.get(key, default)
        try:
            return int(val)
        except (ValueError, TypeError):
            return default

    def get_float(self, key: str, default: float = 0.0) -> float:
        """Retrieves a configuration value coerced to float."""
        val = self.get(key, default)
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

    def load_settings(self) -> Dict[str, Any]:
        """Reads configuration and returns a flat dictionary merged with environment overrides."""
        try:
            config = self.storage.read_config()
        except FileNotFoundError:
            logging.error(
                self._get_string(
                    "settings_manager.not_found",
                    default="Configuration file not found at {path}",
                    path=self.storage.storage_path,
                )
            )
            return {}

        settings_dict: Dict[str, Any] = {}

        # 1. Read mapped keys from sections
        for key, section in self.schema.key_map.items():
            if config.has_section(section) and config.has_option(section, key):
                if self.schema.is_boolean_key(key):
                    try:
                        settings_dict[key] = config.getboolean(section, key)
                    except Exception:
                        settings_dict[key] = config.get(section, key)
                else:
                    settings_dict[key] = config.get(section, key)

        # 2. Backwards compatibility for legacy boolean aliases in INI
        if config.has_section("LOGGING") and config.has_option("LOGGING", "log_step_progress"):
            settings_dict["log_progress"] = config.getboolean("LOGGING", "log_step_progress")
        if config.has_section("UI") and config.has_option("UI", "theme_dark") and "theme_dark" not in settings_dict:
            settings_dict["theme_dark"] = config.getboolean("UI", "theme_dark")

        # 3. 12-Factor App: Apply environment variable overrides
        env_overrides = self.env_provider.get_overrides()
        for settings_key, env_val in env_overrides.items():
            settings_dict[settings_key] = env_val

        # 4. Normalize report aliases (xai_ <-> report_)
        return self.schema.normalize_report_aliases(settings_dict)

    def save_settings(self, new_settings: Dict[str, Any]) -> bool:
        """Updates and persists the provided settings dictionary."""
        try:
            config = self.storage.read_config()
        except FileNotFoundError:
            logging.error(
                self._get_string(
                    "settings_manager.save_not_found",
                    default="Configuration file not found. Unable to save.",
                )
            )
            return False

        has_env_file = getattr(self.env_provider, "has_env_file", lambda: False)()

        # 1. Update INI sections and options
        for key, value in new_settings.items():
            section = self.schema.get_section(key)
            if section:
                # If .env manages DB secrets, keep settings.ini clean with default credentials
                if has_env_file and self.schema.is_secret_key(key):
                    continue

                if not config.has_section(section):
                    config.add_section(section)

                if isinstance(value, bool):
                    config.set(section, key, str(value))
                else:
                    config.set(section, key, str(value))

        # 2. Keep .env in sync with UI/Settings changes for all protected environment variables
        if has_env_file and hasattr(self.env_provider, "sync_variable"):
            settings_to_env = getattr(
                self.env_provider,
                "SETTINGS_TO_ENV_MAP",
                {
                    "monitor_mqtt_host": "CARINA_MQTT_HOST",
                    "monitor_mqtt_port": "CARINA_MQTT_PORT",
                    "db_user": "CARINA_DB_USER",
                    "db_password": "CARINA_DB_PASSWORD",
                    "db_host": "CARINA_DB_HOST",
                    "db_port": "CARINA_DB_PORT",
                    "db_name": "CARINA_DB_NAME",
                    "db_schema": "CARINA_DB_SCHEMA",
                },
            )
            for key, val in new_settings.items():
                if key in settings_to_env and val is not None and str(val) != "":
                    env_var = settings_to_env[key]
                    self.env_provider.sync_variable(env_var, str(val))

        # 3. Persist to storage
        success = self.storage.write_config(config)
        if success:
            logging.info(
                self._get_string(
                    "settings_manager.save_success",
                    default="Settings saved successfully at {path}",
                    path=self.storage.storage_path,
                )
            )
        else:
            logging.error(
                self._get_string(
                    "settings_manager.save_error",
                    default="Failed to write configuration file",
                )
            )
        return success
