# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Defines the SettingsHandler.

The 'save_settings' method now only collects and validates UI data,
returning a dictionary ready to be sent to the backend via SettingsClient.
"""

import configparser
import logging
import os
from typing import Any, Dict, Optional

from ui.handlers.settings_defaults import (
    DEFAULT_SETTINGS_MAP,
    KEY_TO_SECTION_MAP,
    apply_env_overrides,
    sync_env_overrides,
)


class SettingsHandler:
    """
    Manages the logic to load and validate UI settings.
    """

    _KEY_TO_SECTION_MAP = KEY_TO_SECTION_MAP

    def __init__(self, config_path: Optional[str] = None):
        if config_path:
            self.config_path = config_path
        else:
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            self.config_path = os.path.join(project_root, "config", "settings.ini")
        self.config = configparser.ConfigParser()
        self._defaults = self._get_default_settings_map()
        self._current_settings = self.load_settings()
        logging.info("[SettingsHandler] Settings Handler initialized and settings loaded.")

    def load_settings(self) -> Dict[str, Any]:
        """Reads the .ini file and returns a dictionary with the settings."""
        try:
            if not os.path.exists(self.config_path):
                logging.warning(f"[SettingsHandler] File {self.config_path} not found. Using defaults.")
                return self.get_default_settings()

            self.config = configparser.ConfigParser()
            self.config.read(self.config_path, encoding="utf-8")
            loaded_settings = {}
            for key, section in self._KEY_TO_SECTION_MAP.items():
                if self.config.has_option(section, key):
                    value = self.config.get(section, key)
                    if value.lower() in ["true", "false"]:
                        loaded_settings[key] = self.config.getboolean(section, key)
                    elif "." in value:
                        try:
                            loaded_settings[key] = self.config.getfloat(section, key)
                        except ValueError:
                            loaded_settings[key] = value
                    else:
                        try:
                            loaded_settings[key] = self.config.getint(section, key)
                        except ValueError:
                            loaded_settings[key] = value
                else:
                    loaded_settings[key] = self._defaults.get(key)

            for key, value in self._defaults.items():
                if key not in loaded_settings:
                    loaded_settings[key] = value

            apply_env_overrides(loaded_settings, self.config_path)

            return loaded_settings
        except Exception as e:
            logging.error(f"[SettingsHandler] Error loading settings: {e}. Using defaults.", exc_info=True)
            return self.get_default_settings()

    def save_to_file(self, new_settings: Dict[str, Any]) -> bool:
        """
        Persists the provided settings directly to config/settings.ini.
        """
        try:
            self.config = configparser.ConfigParser()
            if os.path.exists(self.config_path):
                self.config.read(self.config_path, encoding="utf-8")

            for key, value in new_settings.items():
                section = self._KEY_TO_SECTION_MAP.get(key)
                if section:
                    if not self.config.has_section(section):
                        self.config.add_section(section)
                    self.config.set(section, key, str(value))

            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                self.config.write(f)

            sync_env_overrides(new_settings, self.config_path)

            logging.info(f"[SettingsHandler] Settings saved successfully to {self.config_path}")
            return True
        except Exception as e:
            logging.error(f"[SettingsHandler] Error saving settings to {self.config_path}: {e}", exc_info=True)
            return False

    def prepare_settings_for_save(self, new_settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates, saves to disk, and updates memory ready for backend IPC.
        """
        self.save_to_file(new_settings)
        self._current_settings.update(new_settings)
        logging.info("[SettingsHandler] New settings saved to disk and prepared for sending to the backend.")
        return new_settings

    def get_current_settings(self) -> Dict[str, Any]:
        self._current_settings = self.load_settings()
        return self._current_settings.copy()

    def get_default_settings(self) -> Dict[str, Any]:
        return self._defaults.copy()

    def _get_default_settings_map(self) -> Dict[str, Any]:
        """Returns the default settings dictionary."""
        return DEFAULT_SETTINGS_MAP.copy()
