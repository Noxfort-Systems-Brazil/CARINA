# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Domain Models and Enums for the CARINA Security Subsystem (SOLID: SRP).
Defines core identity entities, roles, and validation results.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, List, Optional


class UserRole(str, Enum):
    """Available user roles in the system."""
    OPERATOR = "OPERATOR"
    SUPERUSER = "SUPERUSER"
    MASTER = "MASTER"

    @classmethod
    def is_valid_assignable_role(cls, role: str) -> bool:
        """Returns True if the role can be assigned to custom user accounts."""
        return role in (cls.OPERATOR.value, cls.SUPERUSER.value)


@dataclass
class User:
    """Represents a registered user identity in the system."""
    username: str
    role: Any
    password_hash: str = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class AuthResult:
    """Encapsulates the result of an authentication attempt."""
    success: bool
    role_or_error: str = ""
    user: Optional[User] = None
    error_message: str = ""


@dataclass
class PasswordValidationResult:
    """Encapsulates the validation outcome of a password policy check."""
    is_valid: bool
    errors: List[str]
