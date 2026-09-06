# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: src/utils/security_manager.py
# Author: Gabriel Moraes
# Date: September 05, 2026

from typing import Any, Optional

try:
    from src.utils.security.auth_service import AuthService
    from src.utils.security.config import SecurityConfig
    from src.utils.security.hasher import PBKDF2PasswordHasher
    from src.utils.security.interfaces import ILockdownManager, IPasswordHasher, IUserRepository
    from src.utils.security.lockdown import FileLockdownManager
    from src.utils.security.migrator import SecurityStorageMigrator
    from src.utils.security.user_repository import JsonUserRepository
    from src.utils.security.user_service import UserManagementService
except ImportError:
    from utils.security.auth_service import AuthService
    from utils.security.config import SecurityConfig
    from utils.security.hasher import PBKDF2PasswordHasher
    from utils.security.interfaces import ILockdownManager, IPasswordHasher, IUserRepository
    from utils.security.lockdown import FileLockdownManager
    from utils.security.migrator import SecurityStorageMigrator
    from utils.security.user_repository import JsonUserRepository
    from utils.security.user_service import UserManagementService


class SecurityManager:
    """
    Security Subsystem Facade / Orchestrator.
    Exposes a unified public interface while delegating specialized responsibilities
    to AuthService, UserManagementService, ILockdownManager, and IUserRepository.
    Roles available: OPERATOR, SUPERUSER, MASTER.
    """

    def __init__(
        self,
        locale_manager: Optional[object] = None,
        config: Optional[SecurityConfig] = None,
        hasher: Optional[IPasswordHasher] = None,
        lockdown_mgr: Optional[ILockdownManager] = None,
        user_repo: Optional[IUserRepository] = None,
        auth_service: Optional[AuthService] = None,
        user_service: Optional[UserManagementService] = None,
    ):
        self.locale_manager = locale_manager
        self._config = config or SecurityConfig.load_from_env()
        self._hasher = hasher or PBKDF2PasswordHasher()
        self._lockdown_mgr = lockdown_mgr or FileLockdownManager(
            self._config.lockdown_file, locale_manager=self.locale_manager
        )
        self._user_repo = user_repo or JsonUserRepository(
            self._config.security_file, locale_manager=self.locale_manager
        )

        SecurityStorageMigrator.migrate_if_needed(
            self._config.security_file, self._config.lockdown_file, self.locale_manager
        )

        self._auth_service = auth_service or AuthService(
            config=self._config,
            user_repo=self._user_repo,
            hasher=self._hasher,
            lockdown_mgr=self._lockdown_mgr,
            locale_manager=self.locale_manager,
        )
        self._user_service = user_service or UserManagementService(
            config=self._config, user_repo=self._user_repo, hasher=self._hasher, locale_manager=self.locale_manager
        )

        self.max_failed_attempts = self._config.max_failed_attempts
        self._ensure_files()

    # --- Properties for Backward Compatibility ---

    @property
    def security_file(self) -> str:
        return self._config.security_file

    @security_file.setter
    def security_file(self, path: str):
        self._config.security_file = path
        if isinstance(self._user_repo, JsonUserRepository):
            self._user_repo.security_file = path

    @property
    def lockdown_file(self) -> str:
        return self._config.lockdown_file

    @lockdown_file.setter
    def lockdown_file(self, path: str):
        self._config.lockdown_file = path
        if isinstance(self._lockdown_mgr, FileLockdownManager):
            self._lockdown_mgr.lockdown_file = path

    @property
    def is_production(self) -> bool:
        return self._config.is_production

    @is_production.setter
    def is_production(self, val: bool):
        self._config.is_production = val

    @property
    def master_user(self) -> str:
        return self._config.master_user

    @master_user.setter
    def master_user(self, val: str):
        self._config.master_user = val

    @property
    def master_hash(self) -> str:
        return self._config.master_hash

    @master_hash.setter
    def master_hash(self, val: str):
        self._config.master_hash = val

    # --- Internal Helpers / Delegates ---

    def _ensure_files(self) -> None:
        default_hash = self._hasher.hash_password("admin")
        self._user_repo.ensure_default_user(
            is_production=self.is_production, master_user=self.master_user, default_hash=default_hash
        )

    def _hash_password(self, password: str, salt: bytes = None) -> str:
        """Delegates password hashing to the injected IPasswordHasher."""
        return self._hasher.hash_password(password, salt=salt)

    def _verify_password(self, password: str, stored_hash_str: str) -> bool:
        """Delegates password verification to the injected IPasswordHasher."""
        return self._hasher.verify_password(password, stored_hash_str)

    # --- Public API Facade ---

    def is_lockdown(self) -> bool:
        """Checks if system lockdown is currently active."""
        return self._lockdown_mgr.is_active()

    def trigger_lockdown(self) -> None:
        """Creates the persistent lockdown flag."""
        self._lockdown_mgr.activate()

    def clear_lockdown(self) -> None:
        """Removes the persistent lockdown flag and resets failed attempts."""
        self._auth_service.clear_lockdown()

    def record_failed_attempt(self) -> bool:
        """Increments the failed attempt counter and triggers lockdown if threshold reached."""
        return self._auth_service.record_failed_attempt()

    def authenticate(self, username: str, password: str) -> tuple[bool, str]:
        """Attempts to authenticate a user."""
        return self._auth_service.authenticate(username, password)

    def add_user(self, username: str, password: str, role: str) -> bool:
        """Adds or updates a user."""
        return self._user_service.add_user(username, password, role)

    def remove_user(self, username: str) -> bool:
        """Removes a user."""
        return self._user_service.remove_user(username)

    def list_users(self) -> list[dict[str, Any]]:
        """Lists registered users."""
        return self._user_service.list_users()
