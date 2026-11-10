# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Authentication Application Service (Clean Architecture / SOLID: SRP & DIP).
Orchestrates login use cases, delegating lockdown checks to LockdownEnforcer,
credentials verification to CredentialAuthenticator, and master validations to MasterCredentialValidator.
"""

import logging
from typing import Any, Callable, Dict, Optional, Tuple

from src.security.credential_authenticator import CredentialAuthenticator
from src.security.events import (
    AuthenticationFailedEvent,
    LockdownClearedEvent,
    SecurityEvent,
    UserAuthenticatedEvent,
)
from src.security.interfaces import IAuthenticator
from src.security.lockdown_enforcer import LockdownEnforcer
from src.security.master_auth import MasterCredentialValidator
from src.security.models import AuthResult, User, UserRole

logger = logging.getLogger("AuthenticateService")


class AuthenticateService(IAuthenticator):
    """
    Application Service facade responsible for the authentication usecase.
    Orchestrates master identity validation, user credentials evaluation,
    lockdown rate-limiting enforcement, and domain event dispatching.
    """

    def __init__(
        self,
        user_repository: Any = None,
        hasher: Any = None,
        lockdown_manager: Any = None,
        master_validator: Optional[MasterCredentialValidator] = None,
        audit_callback: Optional[Callable[[str, str, str], None]] = None,
        event_dispatcher: Optional[Callable[[SecurityEvent], None]] = None,
        locale_manager: Optional[object] = None,
        db_engine: Optional[Any] = None,
        sync_callback: Optional[Callable[[], None]] = None,
        is_production: bool = False,
        default_dev_password: str = "Admin@Carina2026!",
        config: Optional[Any] = None,
    ):
        # Support legacy signature: (config, user_repo, hasher, lockdown_mgr)
        if hasattr(user_repository, "master_user") and hasattr(user_repository, "security_file"):
            cfg = user_repository
            user_repo = hasher
            pw_hasher = lockdown_manager
            lock_mgr = master_validator
            master_val = MasterCredentialValidator(
                master_user=cfg.master_user,
                master_hash=cfg.master_hash,
                default_user=getattr(cfg, "default_user", "admin"),
                default_hash=getattr(cfg, "default_hash", ""),
                is_production=cfg.is_production,
                hasher=pw_hasher,
            )
            self.config = cfg
            self.user_repository = user_repo
            self.hasher = pw_hasher
            self.lockdown_manager = lock_mgr
            self.master_validator = master_val
            self.is_production = cfg.is_production
            self.default_dev_password = getattr(cfg, "DEFAULT_DEV_PASSWORD", default_dev_password)
        else:
            self.config = config
            self.user_repository = user_repository
            self.hasher = hasher
            self.lockdown_manager = lockdown_manager
            self.master_validator = master_validator
            self.is_production = is_production
            self.default_dev_password = default_dev_password

        if (
            hasattr(self.lockdown_manager, "max_failed_attempts")
            and self.config
            and not getattr(self.lockdown_manager, "_explicit_max", False)
        ):
            self.lockdown_manager.max_failed_attempts = getattr(
                self.config, "max_failed_attempts", self.lockdown_manager.max_failed_attempts
            )

        self.audit_callback = audit_callback
        self.event_dispatcher = event_dispatcher
        self.locale_manager = locale_manager
        self.db_engine = db_engine
        self.sync_callback = sync_callback
        self.last_auth_user: Optional[str] = None

        # Delegated Domain/Application Services (Clean Architecture / SRP)
        self.lockdown_enforcer = LockdownEnforcer(
            lockdown_manager=self.lockdown_manager,
            user_repository=self.user_repository,
            config=self.config,
            event_dispatcher=self._emit_event,
        )
        self.credential_authenticator = CredentialAuthenticator(
            user_repository=self.user_repository,
            hasher=self.hasher,
            db_engine=self.db_engine,
            sync_callback=self.sync_callback,
            is_production=self.is_production,
            default_dev_password=self.default_dev_password,
        )

    def _get_string(self, key: str, default: str = "", **kwargs) -> str:
        if self.locale_manager and hasattr(self.locale_manager, "get_string"):
            try:
                return self.locale_manager.get_string(key, default=default, **kwargs)
            except TypeError:
                res = self.locale_manager.get_string(key, default=default)
                if kwargs and isinstance(res, str):
                    try:
                        return res.format(**kwargs)
                    except Exception:
                        pass
                return res
        return default.format(**kwargs) if default and kwargs else (default or key)

    def _emit_event(self, event: SecurityEvent) -> None:
        if self.event_dispatcher:
            try:
                self.event_dispatcher(event)
            except Exception as e:
                logger.debug(f"[AuthenticateService] Event dispatch failed: {e}")

    def _audit(self, user: str, action: str, details: str = "") -> None:
        if self.audit_callback:
            try:
                self.audit_callback(user, action, details)
            except Exception as e:
                logger.debug(f"[AuthenticateService] Audit logging failed: {e}")

    def is_lockdown(self) -> bool:
        """Returns True if the system is currently in lockdown state."""
        return self.lockdown_enforcer.is_lockdown()

    def clear_lockdown(self) -> None:
        """Removes the lockdown state and resets failed attempt counters."""
        self.lockdown_enforcer.clear_lockdown()

    def record_failed_attempt(self) -> bool:
        """Increments failed attempt counters and triggers lockdown if threshold is met."""
        return self.lockdown_enforcer.record_failed_attempt()

    def authenticate(self, username: str, password: str) -> Tuple[bool, str]:
        """
        Attempts to authenticate credentials against master identities,
        active lockdown state, and registered user accounts.
        Returns (success: bool, role_or_message: str).
        """
        invalid_msg = self._get_string("security_manager.invalid_credentials", default="Invalid credentials")
        system_locked_msg = self._get_string(
            "security_manager.system_locked", default="SYSTEM LOCKED. Only SuperUsers can unlock."
        )

        # 1. Master Fallback Check (Emergency / God Mode)
        if self.master_validator:
            is_master, is_attempt = self.master_validator.verify_master(username, password)
            if is_master:
                self.last_auth_user = username
                if self.is_lockdown():
                    self.clear_lockdown()
                    self._emit_event(LockdownClearedEvent(cleared_by=username))
                self._emit_event(UserAuthenticatedEvent(username=username, role="MASTER"))
                self._audit(username, "AUTH_LOGIN_SUCCESS", "Role: MASTER")
                return True, "MASTER"
            elif is_attempt:
                self.record_failed_attempt()
                self._emit_event(AuthenticationFailedEvent(username=username, reason="Master attempt failed"))
                self._audit(username, "AUTH_LOGIN_FAILED", "Master attempt failed")
                return False, invalid_msg

        users = self.credential_authenticator.fetch_users_map()

        # 2. Lockdown handling: only SUPERUSER can unlock
        if self.is_lockdown():
            if self.credential_authenticator.verify_superuser_unlock(username, password, users):
                self.last_auth_user = username
                self.clear_lockdown()
                self._emit_event(LockdownClearedEvent(cleared_by=username))
                self._emit_event(UserAuthenticatedEvent(username=username, role="SUPERUSER"))
                self._audit(username, "AUTH_LOCKDOWN_UNLOCKED", "SuperUser unlocked system")
                return True, "SUPERUSER"

            self._emit_event(AuthenticationFailedEvent(username=username, reason="System in lockdown"))
            self._audit(username, "AUTH_REJECTED_LOCKDOWN", "System in lockdown")
            return False, system_locked_msg

        # 3. Standard user authentication
        success, role, fail_reason = self.credential_authenticator.verify_credentials(username, password, users)
        if success and role:
            self.last_auth_user = username
            self.lockdown_enforcer.reset_attempts()
            self._emit_event(UserAuthenticatedEvent(username=username, role=role))
            self._audit(username, "AUTH_LOGIN_SUCCESS", f"Role: {role}")
            return True, role

        self.record_failed_attempt()
        reason = fail_reason or "Authentication failed"
        self._emit_event(AuthenticationFailedEvent(username=username, reason=reason))
        audit_action = "AUTH_BLOCKED_DEFAULT_PROD" if reason == "Admin default password rejected" else "AUTH_LOGIN_FAILED"
        self._audit(username, audit_action, reason)
        return False, invalid_msg

    def authenticate_user(self, username: str, password: str) -> AuthResult:
        """Rich DDD authentication returning typed AuthResult domain object."""
        success, role_or_msg = self.authenticate(username, password)
        if success:
            try:
                urole = UserRole(role_or_msg)
            except ValueError:
                urole = UserRole.OPERATOR
            return AuthResult(success=True, user=User(username=username, role=urole))
        return AuthResult(success=False, error_message=role_or_msg)
