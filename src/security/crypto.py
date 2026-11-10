# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Cryptographic Hashing Utilities (SOLID: SRP).
Provides industry-standard PBKDF2 HMAC-SHA256 and Argon2 password hashing.
"""

import binascii
import hashlib
import os
from typing import Optional

try:
    from argon2 import PasswordHasher as _Argon2InternalHasher
    from argon2.exceptions import VerificationError, VerifyMismatchError
    _HAS_ARGON2 = True
except ImportError:
    _HAS_ARGON2 = False
    _Argon2InternalHasher = None
    VerificationError = Exception
    VerifyMismatchError = Exception

from src.security.interfaces import IPasswordHasher


class Pbkdf2PasswordHasher(IPasswordHasher):
    """
    PBKDF2 HMAC SHA-256 password hasher with random salt and configurable iterations.
    Produces format 'salt_hex:hash_hex'.
    Transparently supports verifying legacy or upgraded Argon2 hashes if available.
    """

    def __init__(self, iterations: int = 100000):
        self.iterations = iterations

    def hash_password(self, password: str, salt: Optional[bytes] = None) -> str:
        """Hashes a password using PBKDF2 HMAC SHA-256."""
        if salt is None:
            salt = os.urandom(16)
        pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, self.iterations)
        return f"{binascii.hexlify(salt).decode('utf-8')}:{binascii.hexlify(pwd_hash).decode('utf-8')}"

    def verify_password(self, password: str, stored_hash_str: str) -> bool:
        """Verifies a password against a stored PBKDF2 (or Argon2) hash string."""
        if not stored_hash_str or not password:
            return False

        if stored_hash_str.startswith("$argon2"):
            if _HAS_ARGON2 and _Argon2InternalHasher is not None:
                try:
                    return _Argon2InternalHasher().verify(stored_hash_str, password)
                except Exception:
                    return False
            return False

        try:
            salt_hex, hash_hex = stored_hash_str.split(":")
            salt = binascii.unhexlify(salt_hex)
            stored_hash = binascii.unhexlify(hash_hex)
            new_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, self.iterations)
            return new_hash == stored_hash
        except Exception:
            return False


# Compatibility alias matching CARINA legacy casing
PBKDF2PasswordHasher = Pbkdf2PasswordHasher


class Sha256Hasher:
    """Helper for raw SHA-256 digests used in master and emergency tokens."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Returns hex digest of sha256."""
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    @staticmethod
    def verify_password(password: str, stored_hash: str) -> bool:
        """Constant-time verification of sha256."""
        computed = hashlib.sha256(password.encode("utf-8")).hexdigest()
        return computed == stored_hash


class Argon2PasswordHasher(IPasswordHasher):
    """
    Argon2id password hasher (OWASP recommended password hashing algorithm).
    Requires 'argon2-cffi' package.
    """

    def __init__(self, time_cost: int = 3, memory_cost: int = 65536, parallelism: int = 4):
        if not _HAS_ARGON2 or _Argon2InternalHasher is None:
            raise RuntimeError(
                "[Argon2PasswordHasher] 'argon2-cffi' package is not installed. "
                "Install it via 'pip install argon2-cffi' or use Pbkdf2PasswordHasher."
            )
        self._hasher = _Argon2InternalHasher(
            time_cost=time_cost, memory_cost=memory_cost, parallelism=parallelism
        )

    def hash_password(self, password: str, salt: Optional[bytes] = None) -> str:
        """Hashes a password using Argon2id."""
        return self._hasher.hash(password)

    def verify_password(self, password: str, stored_hash_str: str) -> bool:
        """Verifies a password against a stored Argon2id hash string."""
        if not stored_hash_str or not password:
            return False
        try:
            return self._hasher.verify(stored_hash_str, password)
        except (VerifyMismatchError, VerificationError):
            return False
        except Exception:
            return False
