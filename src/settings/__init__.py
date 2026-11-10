# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Settings subsystem package for CARINA.
Architected according to SOLID principles with segregated interfaces,
isolated persistence, twelve-factor secret providers, and dynamic schema registries.
"""

from settings.env_provider import DotenvSecretProvider
from settings.ini_storage import IniFileStorage
from settings.interfaces import IEnvironmentProvider, ISettingsReader, ISettingsStorage, ISettingsWriter
from settings.schema import SettingsSchema
from settings.service import SettingsService

_default_service = None


def get_settings_service() -> SettingsService:
    """Returns a singleton or default configured instance of SettingsService."""
    global _default_service
    if _default_service is None:
        _default_service = SettingsService()
    return _default_service


__all__ = [
    "ISettingsReader",
    "ISettingsWriter",
    "ISettingsStorage",
    "IEnvironmentProvider",
    "SettingsSchema",
    "IniFileStorage",
    "DotenvSecretProvider",
    "SettingsService",
    "get_settings_service",
]
