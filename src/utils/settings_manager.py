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

# File: src/utils/settings_manager.py
# Author: Gabriel Moraes
# Date: October 22, 2025 (Refactored 2026-09-12 to facade src/settings/ for SOLID compliance)

"""
Backwards-compatibility facade for the settings subsystem.
All modular components, interfaces, and persistence providers are located in `src/settings/`.
"""

import configparser
from typing import Any, Dict, Optional

try:
    from settings import (
        DotenvSecretProvider,
        IEnvironmentProvider,
        IniFileStorage,
        ISettingsReader,
        ISettingsStorage,
        ISettingsWriter,
        SettingsSchema,
        SettingsService,
    )
except ImportError:
    from src.settings import (
        DotenvSecretProvider,
        IEnvironmentProvider,
        IniFileStorage,
        ISettingsReader,
        ISettingsStorage,
        ISettingsWriter,
        SettingsSchema,
        SettingsService,
    )


class SettingsManager(SettingsService):
    """
    Backwards-compatible facade managing reading and writing to the 'settings.ini'
    and .env configuration files, delegating to src/settings/ components.
    """

    _KEY_TO_SECTION_MAP = SettingsSchema.DEFAULT_KEY_TO_SECTION_MAP

    def __init__(self, locale_manager: Optional[Any] = None):
        schema = SettingsSchema(self._KEY_TO_SECTION_MAP)
        storage = IniFileStorage()
        env_provider = DotenvSecretProvider()
        super().__init__(
            storage=storage,
            env_provider=env_provider,
            schema=schema,
            locale_manager=locale_manager,
        )
        self.config_path = self.storage.storage_path


__all__ = [
    "SettingsManager",
    "SettingsService",
    "SettingsSchema",
    "IniFileStorage",
    "DotenvSecretProvider",
    "ISettingsReader",
    "ISettingsWriter",
    "ISettingsStorage",
    "IEnvironmentProvider",
]
