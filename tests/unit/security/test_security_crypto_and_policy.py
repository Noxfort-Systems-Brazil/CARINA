# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Unit Tests for Security Crypto, Hasher, Password Policy, and Field Encryption.
"""

from src.security.crypto import Pbkdf2PasswordHasher, Sha256Hasher
from src.security.field_encryptor import FieldEncryptor
from src.security.interfaces import IPasswordHasher, IPasswordPolicy
from src.security.password_policy import ModernPasswordPolicy


def test_crypto_hasher():
    """Validates PBKDF2 and SHA-256 contracts and salt randomization."""
    hasher = Pbkdf2PasswordHasher(iterations=1000)
    assert isinstance(hasher, IPasswordHasher)

    pwd = "UrbanTraffic2026!Key"
    hash1 = hasher.hash_password(pwd)
    hash2 = hasher.hash_password(pwd)
    assert hash1 != hash2  # Different salts
    assert hasher.verify_password(pwd, hash1) is True
    assert hasher.verify_password(pwd, hash2) is True
    assert hasher.verify_password("WrongPassword", hash1) is False
    assert hasher.verify_password(pwd, "corrupted_hash") is False

    # Sha256 Hasher
    sha_hash = Sha256Hasher.hash_password("master_secret")
    assert Sha256Hasher.verify_password("master_secret", sha_hash) is True
    assert Sha256Hasher.verify_password("wrong", sha_hash) is False


def test_modern_password_policy():
    """Validates OWASP/NIST password complexity policy and UI strength score."""
    policy = ModernPasswordPolicy()
    assert isinstance(policy, IPasswordPolicy)

    # Empty password
    res_empty = policy.validate("")
    assert res_empty.is_valid is False
    assert "vazia" in res_empty.errors[0].lower()

    # Short password (< 8 chars)
    res_short = policy.validate("Aa1!")
    assert res_short.is_valid is False
    assert any("mínimo" in err.lower() for err in res_short.errors)

    # Missing special character
    res_no_spec = policy.validate("ValidPassword123")
    assert res_no_spec.is_valid is False
    assert any("especial" in err.lower() for err in res_no_spec.errors)

    # Valid complex password
    res_valid = policy.validate("SmartCity@2026#Urban")
    assert res_valid.is_valid is True
    assert len(res_valid.errors) == 0

    # UI strength calculation
    strength = policy.calculate_strength("SmartCity@2026#Urban")
    assert strength["is_valid"] is True
    assert strength["score"] >= 4
    assert strength["progress"] >= 0.8


def test_field_encryptor():
    """Validates AES-128-CBC + HMAC-SHA256 authenticated field encryption."""
    key = FieldEncryptor.generate_key()
    encryptor = FieldEncryptor(secret_key=key)

    plain = "SYNAPSE_HFT_GATEWAY_TOKEN_XYZ_2026"
    encrypted = encryptor.encrypt(plain)
    assert encrypted is not None
    assert encrypted != plain
    assert FieldEncryptor.is_encrypted(encrypted) is True

    decrypted = encryptor.decrypt(encrypted)
    assert decrypted == plain

    assert encryptor.encrypt(None) is None
    assert encryptor.decrypt(None) is None
