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

# File: src/settings/__init__.py
# Author: Gabriel Moraes
# Date: 2026-09-12

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
