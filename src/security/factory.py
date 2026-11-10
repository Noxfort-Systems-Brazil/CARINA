# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Security Subsystem Composition Root & Factory (SOLID: DIP, OCP).
Assembles domain, application, and infrastructure security components into a unified subsystem.
Centralizes object instantiation so application facades remain pure orchestrators.
"""

import os
from typing import Any, Optional

from src.security.account_manager import UserAccountManager
from src.security.attempt_store import JsonAttemptStore
from src.security.audit_logger import AuditLogger
from src.security.authenticate_service import AuthenticateService
from src.security.config import SecurityConfig
from src.security.crypto import Pbkdf2PasswordHasher
from src.security.field_encryptor import FieldEncryptor
from src.security.hybrid_user_repo import HybridUserRepository
from src.security.interfaces import (
    IAttemptCounterStore,
    IAuthenticator,
    ILockdownManager,
    IPasswordHasher,
    IPasswordPolicy,
    IUserManagement,
    IUserRepository,
)
from src.security.json_user_repo import JsonUserRepository
from src.security.lockdown_manager import FileLockdownManager
from src.security.master_auth import MasterCredentialValidator
from src.security.password_policy import ModernPasswordPolicy
from src.security.sql_user_repo import SqlUserRepository


class SecurityFactory:
    """
    Composition Root for the CARINA Security Subsystem.
    Provides factory methods to assemble and wire all specialized security components.
    """

    @classmethod
    def create_default(
        cls,
        locale_manager: Optional[object] = None,
        config_dir: Optional[str] = None,
        config: Optional[SecurityConfig] = None,
        hasher: Optional[IPasswordHasher] = None,
        lockdown_manager: Optional[ILockdownManager] = None,
        user_repository: Optional[IUserRepository] = None,
        attempt_store: Optional[IAttemptCounterStore] = None,
        password_policy: Optional[IPasswordPolicy] = None,
        db_engine: Optional[Any] = None,
        field_encryptor: Optional[FieldEncryptor] = None,
        audit_logger: Optional[AuditLogger] = None,
        auth_service: Optional[IAuthenticator] = None,
        account_manager: Optional[IUserManagement] = None,
        is_production: Optional[bool] = None,
        **kwargs: Any,
    ):
        """Constructs a fully wired SecurityManager instance with injected dependencies."""
        from src.security.security_manager import SecurityManager

        # 1. Configuration
        cfg = config or SecurityConfig.load_from_env(config_dir=config_dir)
        if is_production is not None:
            cfg.is_production = is_production
        cfg_dir = getattr(cfg, "config_dir", None) or os.path.dirname(cfg.security_file)

        # 2. Cryptographic Hasher
        pw_hasher = hasher or Pbkdf2PasswordHasher()

        # 3. Rate-Limiting Attempt Store
        store = attempt_store or JsonAttemptStore(cfg.security_file)

        # 4. Lockdown Manager
        lockdown = lockdown_manager or FileLockdownManager(
            lockdown_file=cfg.lockdown_file,
            max_attempts=cfg.max_failed_attempts,
            attempt_store=store,
            locale_manager=locale_manager,
        )
        if hasattr(lockdown, "max_failed_attempts") and cfg and lockdown_manager is None:
            lockdown.max_failed_attempts = cfg.max_failed_attempts

        # 5. User Persistence Repository (Local / Remote / Hybrid)
        if user_repository is not None:
            user_repo = user_repository
        else:
            local_repo = JsonUserRepository(cfg.security_file, locale_manager=locale_manager)
            if db_engine:
                sql_repo = SqlUserRepository(db_engine, locale_manager=locale_manager)
                user_repo = HybridUserRepository(local_repo=local_repo, remote_repo=sql_repo)
            else:
                user_repo = local_repo

        # Initialize storage backend and default user if necessary
        if hasattr(user_repo, "ensure_default_user"):
            user_repo.ensure_default_user(
                is_production=cfg.is_production,
                master_user=cfg.master_user,
                default_hash=pw_hasher.hash_password(cfg.DEFAULT_DEV_PASSWORD),
            )
        elif hasattr(user_repo, "ensure_storage"):
            user_repo.ensure_storage()

        # 6. Master Credential Validator
        master_validator = MasterCredentialValidator(
            is_production=cfg.is_production,
            master_user=cfg.master_user,
            master_hash=cfg.master_hash,
            hasher=pw_hasher,
        )

        # 7. Password Complexity Policy
        pw_policy = password_policy or ModernPasswordPolicy()

        # 8. Audit Logger
        auditor = audit_logger or AuditLogger(
            config_dir=cfg_dir,
            db_engine=db_engine,
            locale_manager=locale_manager,
        )

        # 9. Field Encryptor
        encryptor = field_encryptor or FieldEncryptor()

        # 10. Application Services
        def sync_fn() -> None:
            if hasattr(user_repo, "sync"):
                user_repo.sync()

        def audit_fn(user: str, action: str, details: str = "") -> None:
            auditor.log_action(user, action, details)

        def event_dispatcher(event: Any) -> None:
            auditor.log_event(event)

        authenticator = auth_service or AuthenticateService(
            user_repository=user_repo,
            hasher=pw_hasher,
            lockdown_manager=lockdown,
            master_validator=master_validator,
            audit_callback=audit_fn,
            event_dispatcher=event_dispatcher,
            locale_manager=locale_manager,
            db_engine=db_engine,
            sync_callback=sync_fn,
            is_production=cfg.is_production,
            default_dev_password=cfg.DEFAULT_DEV_PASSWORD,
            config=cfg,
        )

        acct_mgr = account_manager or UserAccountManager(
            user_repository=user_repo,
            hasher=pw_hasher,
            is_protected_master_fn=master_validator.is_protected_master,
            password_policy=pw_policy,
            db_engine=db_engine,
            security_file=cfg.security_file,
            sync_callback=sync_fn,
            audit_callback=audit_fn,
            event_dispatcher=event_dispatcher,
            locale_manager=locale_manager,
        )

        return SecurityManager(
            auth_service=authenticator,
            account_manager=acct_mgr,
            lockdown_manager=lockdown,
            user_repository=user_repo,
            hasher=pw_hasher,
            password_policy=pw_policy,
            master_validator=master_validator,
            attempt_store=store,
            field_encryptor=encryptor,
            audit_logger=auditor,
            config=cfg,
            locale_manager=locale_manager,
            db_engine=db_engine,
        )
