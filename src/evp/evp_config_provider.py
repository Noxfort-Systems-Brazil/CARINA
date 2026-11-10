# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Configuration and Environment Provider for the EVP subsystem (Clean Architecture / Infrastructure).
Isolates the retrieval of environment variables and settings.ini configurations.
"""

import configparser
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class EVPConfigProvider:
    """Loads operational parameters for the EVP subsystem from the environment or INI file."""

    @staticmethod
    def resolve_auto_register_fleet(explicit_value: Optional[bool] = None) -> bool:
        """Determines whether auto-registration of unregistered vehicles is active."""
        if explicit_value is not None:
            return bool(explicit_value)

        env_val = os.getenv("CARINA_AUTO_REGISTER_FLEET")
        if env_val is not None:
            return env_val.strip().lower() in ("true", "1", "yes")

        try:
            cfg = configparser.ConfigParser()
            root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            ini_path = os.path.join(root, "config", "settings.ini")
            if os.path.exists(ini_path):
                cfg.read(ini_path)
            return cfg.getboolean("EVP", "auto_register_fleet", fallback=False)
        except Exception as e:
            logger.debug(f"[EVPConfigProvider] Fallback padrão para auto_register_fleet=False: {e}")
            return False
