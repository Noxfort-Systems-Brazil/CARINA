# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Security Subsystem Thin Facade (SOLID: SRP, DIP & Clean Architecture).
Exposes a unified, high-level API for authentication, user administration,
rate-limiting lockdown, and field encryption by delegating exclusively to SRP services.
Composition and wiring are delegated to SecurityFactory (Composition Root).
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from src.security.config import SecurityConfig
from src.security.field_encryptor import FieldEncryptor
from src.security.interfaces import (
    IAttemptCounterStore,
    IAuthenticator,
    ILockdownManager,
    IPasswordHasher,
    IPasswordPolicy,
    IUserManagement,
    IUserRepository,
)
from src.security.models import AuthResult, PasswordValidationResult

logger = logging.getLogger("SecurityManager")


class SecurityManager(IAuthenticator, IUserManagement):
    """
    Thin Facade for the CARINA Security Subsystem.
    Delegates all business use cases and infrastructure tasks to specialized components:
    - AuthenticateService (Authentication, rate-limiting evaluation, domain events)
    - UserAccountManager (User identity lifecycle & master protection)
    - ILockdownManager (Edge rate-limiting & lockdown state)
    - IPasswordPolicy (Complexity & UI strength computation)
    - FieldEncryptor (AES-128-CBC + HMAC field crypto)
    """

    def __init__(
        self,
        auth_service: Optional[IAuthenticator] = None,
        account_manager: Optional[IUserManagement] = None,
        lockdown_manager: Optional[ILockdownManager] = None,
        user_repository: Optional[IUserRepository] = None,
        hasher: Optional[IPasswordHasher] = None,
        password_policy: Optional[IPasswordPolicy] = None,
        master_validator: Optional[Any] = None,
        attempt_store: Optional[IAttemptCounterStore] = None,
        field_encryptor: Optional[FieldEncryptor] = None,
        audit_logger: Optional[Any] = None,
        config: Optional[SecurityConfig] = None,
        locale_manager: Optional[object] = None,
        config_dir: Optional[str] = None,
        db_engine: Optional[Any] = None,
        # Backward-compatible parameter aliases
        user_repo: Optional[IUserRepository] = None,
        lockdown_mgr: Optional[ILockdownManager] = None,
        user_service: Optional[Any] = None,
        is_production: Optional[bool] = None,
        **kwargs: Any,
    ):
        if auth_service is None or account_manager is None:
            from src.security.factory import SecurityFactory

            instance = SecurityFactory.create_default(
                locale_manager=locale_manager, config_dir=config_dir, config=config, hasher=hasher,
                lockdown_manager=lockdown_manager or lockdown_mgr,
                user_repository=user_repository or user_repo,
                attempt_store=attempt_store, password_policy=password_policy, db_engine=db_engine,
                field_encryptor=field_encryptor, audit_logger=audit_logger,
                auth_service=auth_service, account_manager=account_manager or user_service,
                is_production=is_production, **kwargs,
            )
            self.__dict__.update(instance.__dict__)
            return

        self.auth_service, self.account_manager = auth_service, account_manager
        self.lockdown_manager = lockdown_manager
        self.user_repository = user_repository or user_repo
        self.hasher, self.password_policy = hasher, password_policy
        self.master_validator = master_validator
        self.attempt_store = attempt_store
        self._field_encryptor = field_encryptor
        self.audit_logger, self.config = audit_logger, (config or SecurityConfig())
        self.locale_manager, self.db_engine = locale_manager, db_engine
        if is_production is not None:
            self.is_production = is_production

    # --- Property Accessors ---

    @property
    def authenticator(self) -> IAuthenticator:
        return self.auth_service

    @property
    def security_file(self) -> str:
        return getattr(self.config, "security_file", "")

    @security_file.setter
    def security_file(self, path: str) -> None:
        if self.config:
            self.config.security_file = path
        for target in (self.user_repository, self.attempt_store, self.account_manager):
            if hasattr(target, "security_file"):
                target.security_file = path

    @property
    def lockdown_file(self) -> str:
        return getattr(self.config, "lockdown_file", "")

    @lockdown_file.setter
    def lockdown_file(self, path: str) -> None:
        if self.config:
            self.config.lockdown_file = path
        if hasattr(self.lockdown_manager, "lockdown_file"):
            self.lockdown_manager.lockdown_file = path

    @property
    def is_production(self) -> bool:
        return getattr(self.config, "is_production", False)

    @is_production.setter
    def is_production(self, val: bool) -> None:
        if self.config:
            self.config.is_production = val
        for target in (self.master_validator, self.auth_service):
            if hasattr(target, "is_production"):
                target.is_production = val

    @property
    def master_user(self) -> str:
        return getattr(self.config, "master_user", "")

    @master_user.setter
    def master_user(self, val: str) -> None:
        if self.config:
            self.config.master_user = val
        if hasattr(self.master_validator, "master_user"):
            self.master_validator.master_user = val

    @property
    def master_hash(self) -> str:
        return getattr(self.config, "master_hash", "")

    @master_hash.setter
    def master_hash(self, val: str) -> None:
        if self.config:
            self.config.master_hash = val
        if hasattr(self.master_validator, "master_hash"):
            self.master_validator.master_hash = val

    @property
    def field_encryptor(self) -> Optional[FieldEncryptor]:
        return self._field_encryptor

    @property
    def last_auth_user(self) -> Optional[str]:
        return getattr(self.auth_service, "last_auth_user", None)

    # --- Storage & Setup Helpers ---

    def _ensure_files(self) -> None:
        """Initializes storage backend and ensures default user setup."""
        if hasattr(self.user_repository, "ensure_default_user") and self.hasher and self.config:
            self.user_repository.ensure_default_user(
                is_production=self.config.is_production, master_user=self.config.master_user,
                default_hash=self.hasher.hash_password(self.config.DEFAULT_DEV_PASSWORD),
            )
        elif hasattr(self.user_repository, "ensure_storage"):
            self.user_repository.ensure_storage()

    def _load_db(self) -> Dict[str, Any]:
        """Provides access to underlying user DB structure for tests."""
        if hasattr(self.user_repository, "_load_db"):
            return self.user_repository._load_db()
        users = self.user_repository.fetch_users() if hasattr(self.user_repository, "fetch_users") else {}
        return {"users": users, "failed_attempts": 0}

    def _save_db(self, db: Dict[str, Any]) -> None:
        if hasattr(self.user_repository, "_save_db"):
            self.user_repository._save_db(db)

    def _hash_password(self, password: str, salt: Optional[bytes] = None) -> str:
        return self.hasher.hash_password(password, salt=salt) if self.hasher else ""

    def _verify_password(self, password: str, stored_hash_str: str) -> bool:
        return self.hasher.verify_password(password, stored_hash_str) if self.hasher else False

    # --- Authentication Contract (Delegates to AuthenticateService) ---

    def authenticate(self, username: str, password: str) -> Tuple[bool, str]:
        """Attempts authentication and returns (success: bool, role_or_message: str)."""
        return self.auth_service.authenticate(username, password)

    def authenticate_user(self, username: str, password: str) -> AuthResult:
        """DDD typed authentication returning AuthResult."""
        if hasattr(self.auth_service, "authenticate_user"):
            return self.auth_service.authenticate_user(username, password)
        success, role_or_msg = self.authenticate(username, password)
        return AuthResult(success=success, error_message="" if success else role_or_msg)

    # --- User Management Contract (Delegates to UserAccountManager) ---

    def add_user(self, username: str, password: str, role: str) -> bool:
        """Creates a new user with the specified role."""
        return self.account_manager.add_user(username, password, role)

    def create_user(self, username: str, password: str, role: Any) -> bool:
        """Creates a new user with the specified role (alias)."""
        if hasattr(self.account_manager, "create_user"):
            return self.account_manager.create_user(username, password, role)
        return self.add_user(username, password, str(role))

    def remove_user(self, username: str) -> bool:
        """Removes an existing user."""
        return self.account_manager.remove_user(username)

    def list_users(self) -> List[Dict[str, Any]]:
        """Returns list of registered users and their roles."""
        return self.account_manager.list_users()

    def get_last_account_error(self) -> Optional[str]:
        """Returns the last error message from user account operations."""
        return getattr(self.account_manager, "last_error", None)

    # --- Lockdown & Rate-Limiting (Delegates to ILockdownManager) ---

    def is_lockdown(self) -> bool:
        return self.lockdown_manager.is_lockdown() if self.lockdown_manager else False

    def is_active(self) -> bool:
        return self.is_lockdown()

    def trigger_lockdown(self) -> None:
        if self.lockdown_manager:
            self.lockdown_manager.trigger_lockdown()

    def activate(self) -> None:
        self.trigger_lockdown()

    def clear_lockdown(self) -> None:
        if self.lockdown_manager:
            self.lockdown_manager.clear_lockdown()
        if hasattr(self.user_repository, "reset_failed_attempts"):
            self.user_repository.reset_failed_attempts()

    def clear(self) -> None:
        self.clear_lockdown()

    def record_failed_attempt(self) -> bool:
        return self.lockdown_manager.record_failed_attempt() if self.lockdown_manager else False

    # --- Password Policy & Strength (Delegates to IPasswordPolicy) ---

    def validate_password(self, password: str) -> PasswordValidationResult:
        return self.password_policy.validate(password)

    def calculate_password_strength(self, password: str) -> Dict[str, Any]:
        if hasattr(self.password_policy, "calculate_strength"):
            return self.password_policy.calculate_strength(password)
        from src.security.password_policy import ModernPasswordPolicy

        return ModernPasswordPolicy.calculate_strength(password)
