# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: src/utils/security/migrator.py
# Author: Gabriel Moraes
# Date: September 05, 2026

import logging
import os
import shutil
from typing import Optional

try:
    from utils.paths import get_base_output_dir
except ImportError:
    from src.utils.paths import get_base_output_dir


class SecurityStorageMigrator:
    """
    Handles migration of legacy security and lockdown files to user config directory.
    """

    @classmethod
    def migrate_if_needed(cls, security_file: str, lockdown_file: str, locale_manager: Optional[object] = None) -> None:
        """Checks for legacy files in base_output/results and migrates them if needed."""
        base_results_dir = os.path.join(get_base_output_dir(), "results")
        old_security_file = os.path.join(base_results_dir, "security.json")
        old_lockdown_file = os.path.join(base_results_dir, "lockdown.flag")

        if not os.path.exists(security_file) and os.path.exists(old_security_file):
            try:
                os.makedirs(os.path.dirname(security_file), exist_ok=True)
                shutil.copy2(old_security_file, security_file)
                msg = cls._format_message(
                    locale_manager,
                    "security_manager.migrated_security",
                    default="[SecurityManager] Migrated security.json from {old} to {new}",
                    old=old_security_file,
                    new=security_file,
                )
                logging.info(msg)
            except Exception as e:
                err = cls._format_message(
                    locale_manager,
                    "security_manager.migrate_security_fail",
                    default="[SecurityManager] Failed to migrate security.json: {error}",
                    error=e,
                )
                logging.error(err)

        if not os.path.exists(lockdown_file) and os.path.exists(old_lockdown_file):
            try:
                os.makedirs(os.path.dirname(lockdown_file), exist_ok=True)
                shutil.copy2(old_lockdown_file, lockdown_file)
                msg = cls._format_message(
                    locale_manager,
                    "security_manager.migrated_lockdown",
                    default="[SecurityManager] Migrated lockdown.flag from {old} to {new}",
                    old=old_lockdown_file,
                    new=lockdown_file,
                )
                logging.info(msg)
            except Exception as e:
                err = cls._format_message(
                    locale_manager,
                    "security_manager.migrate_lockdown_fail",
                    default="[SecurityManager] Failed to migrate lockdown.flag: {error}",
                    error=e,
                )
                logging.error(err)

    @staticmethod
    def _format_message(locale_manager: Optional[object], key: str, default: str = "", **kwargs) -> str:
        if locale_manager and hasattr(locale_manager, "get_string"):
            try:
                res = locale_manager.get_string(key, default=default, **kwargs)
                return res
            except TypeError:
                res = locale_manager.get_string(key, default=default)
                if kwargs and isinstance(res, str):
                    try:
                        return res.format(**kwargs)
                    except Exception:
                        pass
                return res
        return default.format(**kwargs) if default and kwargs else (default or key)
