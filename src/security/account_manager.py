# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
User Identity Account Manager Component (SOLID: SRP & DDD).
Coordinates user registration, removal, and listing across storage tiers, emitting domain events.
"""

import logging
import os
from typing import Any, Callable, Dict, List, Optional

from src.security.events import SecurityEvent, UserRegisteredEvent, UserRemovedEvent
from src.security.interfaces import IPasswordHasher, IPasswordPolicy, IUserManagement, IUserRepository
from src.security.password_policy import ModernPasswordPolicy

logger = logging.getLogger("UserAccountManager")


class UserAccountManager(IUserManagement):
    """
    Coordinates user registration, removal, and listing across storage tiers.
    Encapsulates role validation, protection of master accounts, repository sync,
    and domain event dispatching.
    """

    def __init__(
        self,
        user_repository: Any = None,
        hasher: Any = None,
        is_protected_master_fn: Optional[Callable[[str], bool]] = None,
        password_policy: Optional[IPasswordPolicy] = None,
        db_engine: Optional[Any] = None,
        security_file: Optional[str] = None,
        sync_callback: Optional[Callable[[], None]] = None,
        audit_callback: Optional[Callable[[str, str, str], None]] = None,
        event_dispatcher: Optional[Callable[[SecurityEvent], None]] = None,
        locale_manager: Optional[object] = None,
        config: Optional[Any] = None,
    ):
        # Support legacy signature: (config, user_repo, hasher, locale_manager)
        if hasattr(user_repository, "master_user") and hasattr(user_repository, "security_file"):
            cfg = user_repository
            user_repo = hasher
            pwd_hasher = is_protected_master_fn
            self.user_repository = user_repo
            self.hasher = pwd_hasher
            self.is_protected_master_fn = lambda u: u in (cfg.master_user, getattr(cfg, "default_user", "admin"))
            self.security_file = cfg.security_file
            self.config = cfg
        else:
            self.user_repository = user_repository
            self.hasher = hasher
            self.is_protected_master_fn = is_protected_master_fn or (lambda u: False)
            self.security_file = security_file
            self.config = config

        self.password_policy = password_policy or ModernPasswordPolicy()
        self.db_engine = db_engine
        self.sync_callback = sync_callback
        self.audit_callback = audit_callback
        self.event_dispatcher = event_dispatcher
        self.locale_manager = locale_manager
        self.last_error: Optional[str] = None

    def _sync(self) -> None:
        if self.sync_callback:
            try:
                self.sync_callback()
            except Exception as e:
                logger.debug(f"[UserAccountManager] Sync callback failed: {e}")

    def _emit_event(self, event: SecurityEvent) -> None:
        if self.event_dispatcher:
            try:
                self.event_dispatcher(event)
            except Exception as e:
                logger.debug(f"[UserAccountManager] Event dispatch failed: {e}")

    def add_user(self, username: str, password: str, role: Any) -> bool:
        """Creates a new user with the specified role."""
        self.last_error = None
        role_str = role.value if hasattr(role, "value") else str(role or "")
        role_upper = role_str.strip().upper()

        if role_upper not in ["OPERATOR", "SUPERUSER"]:
            self.last_error = f"Nível de acesso inválido: '{role}'."
            return False

        if not username or not password:
            self.last_error = "Nome de usuário e senha são obrigatórios."
            return False

        if self.is_protected_master_fn(username):
            self.last_error = f"Nome de usuário '{username}' é reservado pelo sistema."
            return False

        if self.password_policy:
            val_result = self.password_policy.validate(password)
            if not val_result.is_valid:
                self.last_error = "; ".join(val_result.errors)
                logger.warning(
                    f"[UserAccountManager] Tentativa de cadastro do usuário '{username}' rejeitada: "
                    f"requisitos de senha não atendidos ({self.last_error})"
                )
                return False

        self._sync()

        pwd_hash = self.hasher.hash_password(password)

        if hasattr(self.user_repository, "save_user"):
            saved = self.user_repository.save_user(username, pwd_hash, role_upper)
        elif hasattr(self.user_repository, "set_user"):
            self.user_repository.set_user(username, pwd_hash, role_upper)
            saved = True
        else:
            saved = False

        if saved:
            logger.info(f"[UserAccountManager] User registered/updated: {username} ({role_upper})")
            self._emit_event(UserRegisteredEvent(username=username, role=role_upper))
            if self.audit_callback:
                self.audit_callback(username, "USER_UPSERT", f"Role: {role_upper}")
        return bool(saved)

    def create_user(self, username: str, password: str, role: Any) -> bool:
        """Creates a new user with the specified role (alias for add_user)."""
        return self.add_user(username, password, role)

    def remove_user(self, username: str) -> bool:
        """Removes an existing user. Blocked for master users."""
        self.last_error = None
        if self.is_protected_master_fn(username):
            self.last_error = f"Usuário mestre/reservado '{username}' não pode ser removido."
            logger.warning(f"[UserAccountManager] Blocked attempt to remove protected master user '{username}'.")
            return False

        if hasattr(self.user_repository, "delete_user"):
            removed = self.user_repository.delete_user(username)
        else:
            removed = False

        if removed:
            logger.info(f"[UserAccountManager] User removed: {username}")
            self._emit_event(UserRemovedEvent(username=username))
            if self.audit_callback:
                self.audit_callback(username, "USER_REMOVED", f"User {username} deleted")
            return True
        return False

    def list_users(self) -> List[Dict[str, Any]]:
        """Returns the list of registered users and their roles (excluding passwords)."""
        if self.db_engine:
            if self.security_file and not os.path.exists(self.security_file):
                if hasattr(self.user_repository, "ensure_storage"):
                    self.user_repository.ensure_storage()
            else:
                self._sync()

        if hasattr(self.user_repository, "list_users"):
            return self.user_repository.list_users()
        elif hasattr(self.user_repository, "fetch_users"):
            users = self.user_repository.fetch_users()
            return [{"username": uname, "role": data.get("role", "OPERATOR")} for uname, data in users.items()]
        return []
