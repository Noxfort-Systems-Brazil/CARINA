# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Handles atomic, safe I/O for INI configuration files using configparser.
Complies with Single Responsibility Principle (SRP).
"""

import configparser
import logging
import os
from typing import Optional

from settings.interfaces import ISettingsStorage
from utils.paths import resource_path


class IniFileStorage(ISettingsStorage):
    """Encapsulates disk operations for reading and writing INI configuration files."""

    def __init__(self, file_path: Optional[str] = None):
        if file_path:
            self._file_path = file_path
        else:
            self._file_path = resource_path(os.path.join("config", "settings.ini"))

    @property
    def storage_path(self) -> str:
        return self._file_path

    def exists(self) -> bool:
        """Returns whether the configuration file exists on disk."""
        return os.path.isfile(self._file_path)

    def read_config(self) -> configparser.ConfigParser:
        """
        Reads and parses the INI file from disk.
        Raises FileNotFoundError if the file does not exist.
        """
        config = configparser.ConfigParser()
        if not self.exists():
            logging.error(f"[IniFileStorage] Configuration file not found at {self._file_path}")
            raise FileNotFoundError(f"Settings file not found at {self._file_path}")
        config.read(self._file_path, encoding="utf-8")
        return config

    def write_config(self, config: configparser.ConfigParser) -> bool:
        """
        Atomically writes the ConfigParser structure to the INI file.
        Returns True on success, False on IOError.
        """
        try:
            parent_dir = os.path.dirname(self._file_path)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)

            with open(self._file_path, "w", encoding="utf-8") as configfile:
                config.write(configfile)
            logging.info(f"[IniFileStorage] Settings saved successfully at {self._file_path}")
            return True
        except IOError as e:
            logging.error(f"[IniFileStorage] Failed to write configuration file: {e}")
            return False
