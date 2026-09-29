# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: src/utils/security/interfaces.py
# Author: Gabriel Moraes
# Date: September 05, 2026

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class IPasswordHasher(Protocol):
    """Protocol for hashing and verifying password strings."""

    def hash_password(self, password: str, salt: bytes | None = None) -> str:
        """Hashes a password with an optional salt."""
        ...

    def verify_password(self, password: str, stored_hash_str: str) -> bool:
        """Verifies a password against a stored hash string."""
        ...


@runtime_checkable
class ILockdownManager(Protocol):
    """Protocol for checking, activating, and clearing lockdown states."""

    def is_active(self) -> bool:
        """Returns True if lockdown mode is currently active."""
        ...

    def activate(self) -> None:
        """Triggers the lockdown state."""
        ...

    def clear(self) -> None:
        """Removes the lockdown state."""
        ...


@runtime_checkable
class IUserRepository(Protocol):
    """Protocol for user and authentication storage persistence."""

    def get_user(self, username: str) -> dict[str, Any] | None:
        """Retrieves a user dictionary containing 'hash' and 'role', or None."""
        ...

    def set_user(self, username: str, password_hash: str, role: str) -> bool:
        """Creates or updates a user. Returns True if user already existed (update)."""
        ...

    def delete_user(self, username: str) -> bool:
        """Removes a user by username. Returns True if deleted, False if not found."""
        ...

    def list_users(self) -> list[dict[str, Any]]:
        """Returns a list of dicts with 'username' and 'role'."""
        ...

    def get_failed_attempts(self) -> int:
        """Gets the current number of failed login attempts."""
        ...

    def increment_failed_attempts(self) -> int:
        """Increments the failed attempts counter and returns the new count."""
        ...

    def reset_failed_attempts(self) -> None:
        """Resets the failed attempts counter to 0."""
        ...

    def ensure_default_user(self, is_production: bool, master_user: str, default_hash: str) -> None:
        """Initializes the database file if it does not exist."""
        ...
