# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import hashlib
import os
import shutil
import tempfile

import pytest

from src.security.security_manager import SecurityManager


@pytest.fixture
def temp_security_dir():
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_production_mode_strictly_blocks_admin_admin(temp_security_dir, monkeypatch):
    """Ensures admin:admin is strictly blocked in production environment."""
    monkeypatch.setenv("CARINA_ENV", "production")
    monkeypatch.setenv("CARINA_SUPERUSER_USER", "prod_superuser")
    monkeypatch.setenv("CARINA_SUPERUSER_PASSWORD", "SuperSecurePassword123!")

    sm = SecurityManager()
    sm.security_file = os.path.join(temp_security_dir, "security.json")
    sm.lockdown_file = os.path.join(temp_security_dir, "lockdown.flag")
    sm._ensure_files()

    assert sm.is_production is True
    assert sm.master_user == "prod_superuser"

    # Attempt with admin:admin MUST FAIL
    success, msg = sm.authenticate("admin", "admin")
    assert success is False
    assert "Invalid credentials" in msg or "invalid" in msg.lower()

    # Attempt with real superuser MUST SUCCEED
    success_prod, role = sm.authenticate("prod_superuser", "SuperSecurePassword123!")
    assert success_prod is True
    assert role == "MASTER"


def test_development_mode_allows_github_default_credentials(temp_security_dir, monkeypatch):
    """Ensures secure default credentials work normally in development environment (GitHub clone)."""
    monkeypatch.setenv("CARINA_ENV", "development")
    monkeypatch.delenv("CARINA_SUPERUSER_USER", raising=False)
    monkeypatch.delenv("CARINA_SUPERUSER_PASSWORD", raising=False)
    monkeypatch.delenv("CARINA_SUPERUSER_HASH", raising=False)

    sm = SecurityManager()
    sm.is_production = False
    sm.master_user = "admin"
    sm.master_hash = hashlib.sha256("Admin@Carina2026!".encode("utf-8")).hexdigest()
    sm.security_file = os.path.join(temp_security_dir, "security.json")
    sm.lockdown_file = os.path.join(temp_security_dir, "lockdown.flag")
    sm._ensure_files()

    assert sm.is_production is False
    assert sm.master_user == "admin"

    # admin with default GitHub password MUST SUCCEED in development mode
    success, role = sm.authenticate("admin", "Admin@Carina2026!")
    assert success is True
    assert role in ["SUPERUSER", "MASTER"]


def test_local_superuser_noxfort_credentials(temp_security_dir, monkeypatch):
    """Ensures local superuser_noxfort credentials work and authenticate as MASTER."""
    monkeypatch.setenv("CARINA_ENV", "development")
    monkeypatch.setenv("CARINA_SUPERUSER_USER", "superuser_noxfort")
    monkeypatch.setenv("CARINA_SUPERUSER_PASSWORD", "7K2%,3a&C-KJDqh%jFN37^{v")

    sm = SecurityManager()
    sm.security_file = os.path.join(temp_security_dir, "security.json")
    sm.lockdown_file = os.path.join(temp_security_dir, "lockdown.flag")
    sm._ensure_files()

    assert sm.master_user == "superuser_noxfort"
    success, role = sm.authenticate("superuser_noxfort", "7K2%,3a&C-KJDqh%jFN37^{v")
    assert success is True
    assert role == "MASTER"


def test_add_user_allows_update_and_blocks_insecure_pwd_in_prod(temp_security_dir, monkeypatch):
    """Ensures password updates work and 'admin' password is blocked in production."""
    monkeypatch.setenv("CARINA_ENV", "production")
    monkeypatch.setenv("CARINA_SUPERUSER_USER", "prod_master")
    monkeypatch.setenv("CARINA_SUPERUSER_PASSWORD", "Secret123!")

    sm = SecurityManager()
    sm.security_file = os.path.join(temp_security_dir, "security.json")
    sm.lockdown_file = os.path.join(temp_security_dir, "lockdown.flag")
    sm._ensure_files()

    # In production, adding or changing password to 'admin' must be rejected
    assert sm.add_user("testuser", "admin", "SUPERUSER") is False

    # Adding with strong password should succeed
    assert sm.add_user("testuser", "StrongPass456!", "SUPERUSER") is True

    # Updating existing password should succeed
    assert sm.add_user("testuser", "NewStrongPass789!", "SUPERUSER") is True
    success, role = sm.authenticate("testuser", "NewStrongPass789!")
    assert success is True
    assert role == "SUPERUSER"


def test_security_manager_with_sql_engine(temp_security_dir, monkeypatch):
    """Ensures SecurityManager operates seamlessly using SqlUserRepository and field_encryptor."""
    import sqlite3
    from src.security.field_encryptor import FieldEncryptor

    class MockEngine:
        def __init__(self):
            self.db_type = "sqlite"
            self.is_shared_connection = True
            self._conn = sqlite3.connect(":memory:")

        def get_connection(self):
            return self._conn

    engine = MockEngine()
    key = FieldEncryptor.generate_key()
    monkeypatch.setenv("CARINA_SECRET_KEY", key)

    sm = SecurityManager(db_engine=engine)
    sm.lockdown_file = os.path.join(temp_security_dir, "lockdown.flag")
    sm._ensure_files()

    # Authenticate default dev admin
    success, role = sm.authenticate("admin", "Admin@Carina2026!")
    assert success is True
    assert role in ["SUPERUSER", "MASTER"]

    # Add a user via SQL repo
    assert sm.add_user("sql_op", "Operator@2026!Sec", "OPERATOR") is True
    success_op, role_op = sm.authenticate("sql_op", "Operator@2026!Sec")
    assert success_op is True
    assert role_op == "OPERATOR"

    # FieldEncryptor integration
    token = "EVP_FLEET_VEHICLE_TOKEN_999"
    crypted = sm.field_encryptor.encrypt(token)
    assert crypted != token
    assert sm.field_encryptor.decrypt(crypted) == token

