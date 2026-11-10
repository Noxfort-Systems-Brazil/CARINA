# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from src.security.field_encryptor import FieldEncryptor


def test_field_encryptor_roundtrip():
    key = FieldEncryptor.generate_key()
    encryptor = FieldEncryptor(secret_key=key)

    original = "MySecretFleetToken12345"
    encrypted = encryptor.encrypt(original)

    assert encrypted != original
    assert FieldEncryptor.is_encrypted(encrypted) is True

    decrypted = encryptor.decrypt(encrypted)
    assert decrypted == original


def test_field_encryptor_different_ciphers_same_plaintext():
    key = FieldEncryptor.generate_key()
    encryptor = FieldEncryptor(secret_key=key)

    original = "TokenRepeatTest"
    enc1 = encryptor.encrypt(original)
    enc2 = encryptor.encrypt(original)

    # Fernet generates fresh random 16-byte IV for each encryption
    assert enc1 != enc2
    assert encryptor.decrypt(enc1) == original
    assert encryptor.decrypt(enc2) == original


def test_field_encryptor_wrong_key_fails():
    key1 = FieldEncryptor.generate_key()
    key2 = FieldEncryptor.generate_key()

    enc1 = FieldEncryptor(secret_key=key1)
    enc2 = FieldEncryptor(secret_key=key2)

    cipher = enc1.encrypt("SecretPayload")

    with pytest.raises(ValueError, match="Decryption failed"):
        enc2.decrypt(cipher)


def test_field_encryptor_none_and_empty():
    encryptor = FieldEncryptor()
    assert encryptor.encrypt(None) is None
    assert encryptor.encrypt("") == ""
    assert encryptor.decrypt(None) is None
    assert encryptor.decrypt("") == ""


def test_field_encryptor_is_encrypted_heuristic():
    assert FieldEncryptor.is_encrypted(None) is False
    assert FieldEncryptor.is_encrypted("") is False
    assert FieldEncryptor.is_encrypted("not_encrypted_string") is False

    key = FieldEncryptor.generate_key()
    enc = FieldEncryptor(key).encrypt("test")
    assert FieldEncryptor.is_encrypted(enc) is True
