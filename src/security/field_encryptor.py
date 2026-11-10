# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Field-Level Encryption Component (SOLID: SRP).
Provides symmetric authenticated field encryption using AES-128-CBC + HMAC-SHA256 (Fernet).
"""

import base64
import logging
import os
from typing import Optional, Union

try:
    from cryptography.fernet import Fernet, InvalidToken
    _HAS_CRYPTOGRAPHY = True
except ImportError:
    _HAS_CRYPTOGRAPHY = False
    Fernet = None
    InvalidToken = Exception


class FieldEncryptor:
    """
    Symmetric field-level encryption service using AES-128-CBC + HMAC-SHA256 (Fernet).
    Guarantees authenticated ciphertext with integrity checks across SQLite and PostgreSQL.
    """

    def __init__(self, secret_key: Optional[Union[str, bytes]] = None):
        if not _HAS_CRYPTOGRAPHY:
            raise RuntimeError(
                "[FieldEncryptor] 'cryptography' library is not available. "
                "Install it via 'pip install cryptography' to use field-level encryption."
            )

        resolved_key = secret_key or os.getenv("CARINA_SECRET_KEY", "").strip()

        if not resolved_key:
            ephemeral = Fernet.generate_key()
            self._fernet = Fernet(ephemeral)
            self._key_str = ephemeral.decode("utf-8")
            logging.warning(
                "[FieldEncryptor] CARINA_SECRET_KEY not set. Using ephemeral in-memory encryption key. "
                "Encrypted data will not be recoverable across process restarts. Set CARINA_SECRET_KEY in .env!"
            )
        else:
            if isinstance(resolved_key, str):
                resolved_key_bytes = resolved_key.encode("utf-8")
            else:
                resolved_key_bytes = resolved_key

            try:
                self._fernet = Fernet(resolved_key_bytes)
                self._key_str = resolved_key_bytes.decode("utf-8")
            except Exception as e:
                raise ValueError(
                    f"[FieldEncryptor] Invalid Fernet secret key provided. "
                    f"Keys must be 32 url-safe base64-encoded bytes. Error: {e}"
                )

    @classmethod
    def generate_key(cls) -> str:
        """Generates a secure, 32 url-safe base64-encoded Fernet key for .env configuration."""
        if not _HAS_CRYPTOGRAPHY:
            raise RuntimeError("[FieldEncryptor] cryptography is not installed.")
        return Fernet.generate_key().decode("utf-8")

    def encrypt(self, plain_text: Optional[str]) -> Optional[str]:
        """
        Encrypts a plaintext string into a Fernet-encoded ciphertext string.
        Returns None if input is None, or empty string if input is empty.
        """
        if plain_text is None:
            return None
        if plain_text == "":
            return ""

        cipher_bytes = self._fernet.encrypt(plain_text.encode("utf-8"))
        return cipher_bytes.decode("utf-8")

    def decrypt(self, cipher_text: Optional[str]) -> Optional[str]:
        """
        Decrypts a Fernet ciphertext string back to plaintext.
        Returns None if input is None, or empty string if input is empty.
        """
        if cipher_text is None:
            return None
        if cipher_text == "":
            return ""

        try:
            plain_bytes = self._fernet.decrypt(cipher_text.encode("utf-8"))
            return plain_bytes.decode("utf-8")
        except InvalidToken:
            raise ValueError("[FieldEncryptor] Decryption failed: invalid token or wrong secret key.")
        except Exception as e:
            raise ValueError(f"[FieldEncryptor] Unexpected error during decryption: {e}")

    @staticmethod
    def is_encrypted(value: Optional[str]) -> bool:
        """
        Heuristic test to check if a string appears to be a Fernet encrypted token.
        Fernet tokens start with 'gAAAAA' (Base64 for version 0x80 + 8-byte timestamp).
        """
        if not value or not isinstance(value, str):
            return False
        return value.startswith("gAAAAA") and len(value) >= 100
