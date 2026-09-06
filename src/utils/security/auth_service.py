# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: src/utils/security/auth_service.py
# Author: Gabriel Moraes
# Date: September 05, 2026

import hashlib
import logging
from typing import Optional

from src.utils.security.config import SecurityConfig
from src.utils.security.interfaces import ILockdownManager, IPasswordHasher, IUserRepository


class AuthService:
    """
    Handles authentication policies, brute-force defense, lockdown unlock rules,
    and credential verification.
    """

    def __init__(
        self,
        config: SecurityConfig,
        user_repo: IUserRepository,
        hasher: IPasswordHasher,
        lockdown_mgr: ILockdownManager,
        locale_manager: Optional[object] = None,
    ):
        self.config = config
        self.user_repo = user_repo
        self.hasher = hasher
        self.lockdown_mgr = lockdown_mgr
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

    def record_failed_attempt(self) -> bool:
        """
        Increments failed attempts and triggers lockdown if the threshold is reached.
        Returns True if lockdown was triggered or already active.
        """
        if self.lockdown_mgr.is_active():
            return True

        new_count = self.user_repo.increment_failed_attempts()
        logging.warning(
            self._get_string(
                "security_manager.failed_attempt_registered",
                default="[SecurityManager] Failed login attempt recorded. Total: {current}/{max}",
                current=new_count,
                max=self.config.max_failed_attempts,
            )
        )

        if new_count >= self.config.max_failed_attempts:
            self.lockdown_mgr.activate()
            return True

        return False

    def clear_lockdown(self) -> None:
        """Removes the lockdown state and resets failed attempt counter."""
        self.lockdown_mgr.clear()
        self.user_repo.reset_failed_attempts()
        logging.info(
            self._get_string(
                "security_manager.lockdown_cleared",
                default="[SecurityManager] Lockdown removed and failed attempts counter reset.",
            )
        )

    def authenticate(self, username: str, password: str) -> tuple[bool, str]:
        """
        Authenticates credentials against master fallback, lockdown rules, and registered users.
        Returns: (success_bool, role_or_error_msg)
        """
        invalid_msg = self._get_string("security_manager.invalid_credentials", default="Invalid credentials")
        system_locked_msg = self._get_string(
            "security_manager.system_locked", default="SYSTEM LOCKED. Only SuperUsers can unlock."
        )

        # STRICT PRODUCTION SECURITY RULE:
        # Default test credentials 'admin:admin' are strictly blocked in production!
        if self.config.is_production and username == "admin" and password == "admin":
            logging.warning(
                self._get_string(
                    "security_manager.admin_blocked_prod",
                    default="[SecurityManager] 🚨 Default 'admin:admin' credentials blocked in production environment.",
                )
            )
            self.record_failed_attempt()
            return False, invalid_msg

        # Master Fallback Check
        if username == self.config.master_user:
            raw_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
            if raw_hash == self.config.master_hash:
                if self.lockdown_mgr.is_active():
                    self.clear_lockdown()
                return True, "MASTER"
            else:
                self.record_failed_attempt()
                return False, invalid_msg

        # Lockdown Protection Check
        if self.lockdown_mgr.is_active():
            user_data = self.user_repo.get_user(username)
            if user_data and user_data.get("role") == "SUPERUSER":
                if self.config.is_production and username == "admin" and password == "admin":
                    return False, system_locked_msg
                if self.hasher.verify_password(password, user_data.get("hash", "")):
                    self.clear_lockdown()
                    return True, "SUPERUSER"

            return False, system_locked_msg

        # Normal User Authentication
        user_data = self.user_repo.get_user(username)
        if not user_data:
            self.record_failed_attempt()
            return False, invalid_msg

        # Block default 'admin' account credentials in production if unchanged
        if (
            self.config.is_production
            and username == "admin"
            and self.hasher.verify_password("admin", user_data.get("hash", ""))
        ):
            logging.warning(
                "[SecurityManager] 🚨 Insecure default 'admin' account credentials blocked in production environment."
            )
            self.record_failed_attempt()
            return False, invalid_msg

        if self.hasher.verify_password(password, user_data.get("hash", "")):
            self.user_repo.reset_failed_attempts()
            return True, user_data.get("role", "OPERATOR")
        else:
            self.record_failed_attempt()
            return False, invalid_msg
