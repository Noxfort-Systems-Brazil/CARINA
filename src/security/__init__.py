# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
CARINA Security Subsystem (Clean Architecture, SOLID & DDD).
Provides authentication, rate-limiting, user identities, field encryption,
audit trails, and offline-first hybrid resilience for Smart Cities.
"""

from src.security.account_manager import UserAccountManager
from src.security.attempt_store import JsonAttemptStore, MemoryAttemptStore
from src.security.audit_logger import AuditLogger
from src.security.authenticate_service import AuthenticateService
from src.security.config import SecurityConfig
from src.security.crypto import Argon2PasswordHasher, PBKDF2PasswordHasher, Pbkdf2PasswordHasher, Sha256Hasher
from src.security.events import (
    AuthenticationFailedEvent,
    LockdownClearedEvent,
    LockdownTriggeredEvent,
    SecurityEvent,
    UserAuthenticatedEvent,
    UserRegisteredEvent,
    UserRemovedEvent,
)
from src.security.factory import SecurityFactory
from src.security.field_encryptor import FieldEncryptor
from src.security.hybrid_user_repo import HybridUserRepository
from src.security.interfaces import (
    IAttemptCounterStore,
    IAuthenticator,
    ILockdownManager,
    IPasswordHasher,
    IPasswordPolicy,
    ISynchronizable,
    IUserManagement,
    IUserRepository,
)
from src.security.json_user_repo import InMemoryUserRepository, JsonUserRepository
from src.security.lockdown_manager import FileLockdownManager, InMemoryLockdownManager
from src.security.master_auth import MasterCredentialValidator
from src.security.models import AuthResult, PasswordValidationResult, User, UserRole
from src.security.password_policy import ModernPasswordPolicy, PasswordValidator
from src.security.security_manager import SecurityManager
from src.security.sql_user_repo import SqlUserRepository

# Aliases for seamless backward compatibility
AuthService = AuthenticateService
UserManagementService = UserAccountManager

__all__ = [
    "SecurityManager",
    "SecurityFactory",
    "SecurityConfig",
    "UserRole",
    "User",
    "AuthResult",
    "PasswordValidationResult",
    "IPasswordHasher",
    "IUserRepository",
    "ISynchronizable",
    "IAttemptCounterStore",
    "ILockdownManager",
    "IAuthenticator",
    "IUserManagement",
    "IPasswordPolicy",
    "Pbkdf2PasswordHasher",
    "PBKDF2PasswordHasher",
    "Sha256Hasher",
    "Argon2PasswordHasher",
    "ModernPasswordPolicy",
    "PasswordValidator",
    "FileLockdownManager",
    "InMemoryLockdownManager",
    "MasterCredentialValidator",
    "AuthenticateService",
    "AuthService",
    "UserAccountManager",
    "UserManagementService",
    "FieldEncryptor",
    "AuditLogger",
    "JsonAttemptStore",
    "MemoryAttemptStore",
    "JsonUserRepository",
    "InMemoryUserRepository",
    "SqlUserRepository",
    "HybridUserRepository",
    "SecurityEvent",
    "UserAuthenticatedEvent",
    "AuthenticationFailedEvent",
    "LockdownTriggeredEvent",
    "LockdownClearedEvent",
    "UserRegisteredEvent",
    "UserRemovedEvent",
]
