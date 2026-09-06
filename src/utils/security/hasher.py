# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: src/utils/security/hasher.py
# Author: Gabriel Moraes
# Date: September 05, 2026

import binascii
import hashlib
import os
from typing import Optional

from src.utils.security.interfaces import IPasswordHasher


class PBKDF2PasswordHasher(IPasswordHasher):
    """
    PBKDF2 HMAC SHA-256 password hasher with random 16-byte salt and 100,000 iterations.
    Produces format 'salt_hex:hash_hex'.
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
        """Verifies a password against a stored PBKDF2 hash string."""
        try:
            salt_hex, hash_hex = stored_hash_str.split(":")
            salt = binascii.unhexlify(salt_hex)
            stored_hash = binascii.unhexlify(hash_hex)
            new_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, self.iterations)
            return new_hash == stored_hash
        except Exception:
            return False
