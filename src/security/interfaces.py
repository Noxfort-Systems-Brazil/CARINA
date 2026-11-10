# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Security Subsystem Protocol Contracts (SOLID: ISP & DIP).
Defines segregated protocols for password hashing, user persistence,
lockdown management, synchronization, and user administration.
"""

from typing import Any, Dict, List, Optional, Protocol, Tuple, runtime_checkable

from src.security.models import PasswordValidationResult


@runtime_checkable
class IPasswordHasher(Protocol):
    """Contract for password hashing and verification algorithms."""

    def hash_password(self, password: str, salt: Optional[bytes] = None) -> str:
        """Hashes a password with an optional salt and returns a serialized hash string."""
        ...

    def verify_password(self, password: str, stored_hash_str: str) -> bool:
        """Verifies a plain password against the serialized hash string."""
        ...


@runtime_checkable
class IUserRepository(Protocol):
    """Contract for user identity storage and persistence (pure CRUD)."""

    def ensure_storage(self) -> None:
        """Ensures the underlying storage backend exists and is ready."""
        ...

    def fetch_users(self) -> Dict[str, Dict[str, str]]:
        """Loads all registered users as a mapping of username -> {'hash': ..., 'role': ...}."""
        ...

    def save_user(self, username: str, password_hash: str, role: str) -> bool:
        """Persists or updates a user credential record."""
        ...

    def delete_user(self, username: str) -> bool:
        """Deletes a user record by username."""
        ...


@runtime_checkable
class ISynchronizable(Protocol):
    """Contract for repositories or services supporting distributed data reconciliation."""

    def sync(self) -> None:
        """Synchronizes data across local cache and central database."""
        ...


@runtime_checkable
class IAttemptCounterStore(Protocol):
    """Contract for persisting rate-limiting failed attempt counters."""

    def get_failed_attempts(self) -> int:
        """Returns the recorded count of failed authentication attempts."""
        ...

    def set_failed_attempts(self, count: int) -> None:
        """Persists the updated count of failed authentication attempts."""
        ...


@runtime_checkable
class ILockdownManager(Protocol):
    """Contract for rate limiting and lockdown failsafe management."""

    def is_lockdown(self) -> bool:
        """Returns True if the system is currently under persistent lockdown."""
        ...

    def trigger_lockdown(self) -> None:
        """Activates the persistent lockdown state."""
        ...

    def clear_lockdown(self) -> None:
        """Removes lockdown state and resets failed attempt counters."""
        ...

    def record_failed_attempt(self) -> bool:
        """
        Increments failed login attempts and triggers lockdown if threshold is met.
        Returns True if lockdown is active or was triggered during this call.
        """
        ...


@runtime_checkable
class IAuthenticator(Protocol):
    """Minimal contract for components that only need to authenticate user credentials."""

    def authenticate(self, username: str, password: str) -> Tuple[bool, str]:
        """
        Attempts to authenticate a user.
        Returns (success_bool, role_string_or_error_msg).
        """
        ...


@runtime_checkable
class IUserManagement(Protocol):
    """Contract for components managing user accounts (CRUD)."""

    def add_user(self, username: str, password: str, role: str) -> bool:
        """Creates a new user with the specified role."""
        ...

    def remove_user(self, username: str) -> bool:
        """Removes an existing user."""
        ...

    def list_users(self) -> List[Dict[str, Any]]:
        """Returns list of registered users and their roles (excluding credentials)."""
        ...


@runtime_checkable
class IPasswordPolicy(Protocol):
    """Contract for password complexity and security policy validators (SOLID: ISP)."""

    def validate(self, password: str) -> PasswordValidationResult:
        """
        Validates the given plaintext password against complexity requirements.
        Returns a PasswordValidationResult containing is_valid and list of errors.
        """
        ...


@runtime_checkable
class ISecurityStateRepository(Protocol):
    """Contract for security state and persistent rate-limiting failed attempts (SOLID / DDD)."""

    def ensure_storage(self) -> None:
        """Ensures the security state table exists."""
        ...

    def get_failed_attempts(self) -> int:
        """Returns the recorded count of failed authentication attempts."""
        ...

    def increment_failed_attempts(self) -> int:
        """Increments failed attempt counter atomically and returns the new count."""
        ...

    def reset_failed_attempts(self) -> None:
        """Resets failed attempts to 0."""
        ...
