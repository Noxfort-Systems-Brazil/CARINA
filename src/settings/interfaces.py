# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Defines abstract contracts for the CARINA settings subsystem.
Complies with Interface Segregation Principle (ISP) and Dependency Inversion Principle (DIP).
"""

import configparser
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class ISettingsReader(ABC):
    """Interface for reading configuration settings (ISP - Read-only clients)."""

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value by key, returning default if not found."""
        pass

    @abstractmethod
    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get a setting value as boolean."""
        pass

    @abstractmethod
    def get_int(self, key: str, default: int = 0) -> int:
        """Get a setting value as integer."""
        pass

    @abstractmethod
    def get_float(self, key: str, default: float = 0.0) -> float:
        """Get a setting value as float."""
        pass

    @abstractmethod
    def load_settings(self) -> Dict[str, Any]:
        """Loads and returns all settings as a flat dictionary."""
        pass


class ISettingsWriter(ABC):
    """Interface for saving configuration settings (ISP - Writer clients)."""

    @abstractmethod
    def save_settings(self, new_settings: Dict[str, Any]) -> bool:
        """Updates and persists the provided settings dictionary."""
        pass


class ISettingsStorage(ABC):
    """Interface for low-level configuration persistence backend (INI, JSON, SQLite, etc.)."""

    @abstractmethod
    def read_config(self) -> configparser.ConfigParser:
        """Reads raw configuration parser from storage."""
        pass

    @abstractmethod
    def write_config(self, config: configparser.ConfigParser) -> bool:
        """Writes raw configuration parser to storage."""
        pass

    @property
    @abstractmethod
    def storage_path(self) -> str:
        """Returns the absolute or display path to the storage file/resource."""
        pass


class IEnvironmentProvider(ABC):
    """Interface for 12-Factor App secrets and environment variable integration."""

    @abstractmethod
    def load_env(self) -> None:
        """Loads environment variables from disk (e.g. .env)."""
        pass

    @abstractmethod
    def get_overrides(self) -> Dict[str, str]:
        """Returns dictionary of setting_key -> environment_value overrides."""
        pass

    @abstractmethod
    def sync_variable(self, env_key: str, value: str) -> bool:
        """Synchronizes an environment variable in-memory and in persistent .env if present."""
        pass

    @abstractmethod
    def has_env_file(self) -> bool:
        """Returns True if a persistent environment/secrets file is configured and exists."""
        pass
