# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: src/utils/security/user_service.py
# Author: Gabriel Moraes
# Date: September 05, 2026

import logging
from typing import Any, Optional

from src.utils.security.config import SecurityConfig
from src.utils.security.interfaces import IPasswordHasher, IUserRepository


class UserManagementService:
    """
    Handles user administration, roles validation, and user lifecycle operations.
    """

    def __init__(
        self,
        config: SecurityConfig,
        user_repo: IUserRepository,
        hasher: IPasswordHasher,
        locale_manager: Optional[object] = None,
    ):
        self.config = config
        self.user_repo = user_repo
        self.hasher = hasher
        self.locale_manager = locale_manager

    def _get_string(self, key: str, default: str = "", **kwargs) -> str:
        if self.locale_manager and hasattr(self.locale_manager, "get_string"):
            try:
                res = self.locale_manager.get_string(key, default=default, **kwargs)
                return res
            except TypeError:
                res = self.locale_manager.get_string(key, default=default)
                if kwargs and isinstance(res, str):
                    try:
                        return res.format(**kwargs)
                    except Exception:
                        pass
                return res
        return default.format(**kwargs) if default and kwargs else (default or key)

    def add_user(self, username: str, password: str, role: str) -> bool:
        """Adds or updates a user in the repository with role and password checks."""
        if role not in ["OPERATOR", "SUPERUSER"]:
            return False

        if self.config.is_production and password == "admin":
            logging.warning("[SecurityManager] Insecure password 'admin' rejected in production.")
            return False

        pwd_hash = self.hasher.hash_password(password)
        is_update = self.user_repo.set_user(username, pwd_hash, role)

        log_key = "security_manager.user_updated" if is_update else "security_manager.user_added"
        default_log = (
            "[SecurityManager] User updated: {username} ({role})"
            if is_update
            else "[SecurityManager] New user registered: {username} ({role})"
        )
        logging.info(self._get_string(log_key, default=default_log, username=username, role=role))
        return True

    def remove_user(self, username: str) -> bool:
        """Removes a user with guardrails protecting master and dev admin users."""
        if username == self.config.master_user:
            logging.warning(f"[SecurityManager] Blocked attempt to remove master user '{username}'.")
            return False

        if not self.config.is_production and username == "admin":
            logging.warning(
                self._get_string(
                    "security_manager.admin_remove_blocked",
                    default="[SecurityManager] Blocked attempt to remove 'admin' user.",
                )
            )
            return False

        if self.user_repo.delete_user(username):
            logging.info(
                self._get_string(
                    "security_manager.user_removed",
                    default="[SecurityManager] User removed: {username}",
                    username=username,
                )
            )
            return True
        return False

    def list_users(self) -> list[dict[str, Any]]:
        """Returns the list of registered users."""
        return self.user_repo.list_users()
