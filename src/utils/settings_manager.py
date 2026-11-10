# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Backwards-compatibility facade for the settings subsystem.
All modular components, interfaces, and persistence providers are located in `src/settings/`.
"""

import configparser
from typing import Any, Dict, Optional

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
