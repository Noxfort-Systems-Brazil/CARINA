# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Backwards-compatibility facade for settings defaults and section mappings.
Delegates core configuration and environment variables to the backend `src/settings` subsystem,
preserving Clean Architecture (Dependency Rule) and SRP.
"""

import os
from typing import Any, Dict

from src.settings.defaults import DEFAULT_SETTINGS_MAP
from src.settings.env_provider import DotenvSecretProvider
from src.settings.schema import SettingsSchema

KEY_TO_SECTION_MAP: Dict[str, str] = SettingsSchema.DEFAULT_KEY_TO_SECTION_MAP


def _get_provider(config_path: str = "") -> DotenvSecretProvider:
    if config_path:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(config_path)))
        env_file = os.path.join(project_root, ".env")
        return DotenvSecretProvider(env_file)
    return DotenvSecretProvider()


def apply_env_overrides(settings: Dict[str, Any], config_path: str = "") -> None:
    """Delegates environment variable injection to DotenvSecretProvider."""
    provider = _get_provider(config_path)
    overrides = provider.get_overrides()
    schema = SettingsSchema()
    for k, v in overrides.items():
        if schema.is_boolean_key(k):
            settings[k] = str(v).strip().lower() in ("true", "1", "yes", "on")
        else:
            settings[k] = v


def sync_env_overrides(settings: Dict[str, Any], config_path: str = "") -> None:
    """Delegates environment variable synchronization to DotenvSecretProvider."""
    provider = _get_provider(config_path)
    if not provider.has_env_file():
        return
    env_map = provider.SETTINGS_TO_ENV_MAP
    for set_k, env_k in env_map.items():
        if set_k in settings and settings[set_k] is not None and str(settings[set_k]) != "":
            provider.sync_variable(env_k, str(settings[set_k]))
