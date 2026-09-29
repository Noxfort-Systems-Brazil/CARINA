# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: tests/unit/test_security_modular.py
# Author: Gabriel Moraes
# Date: September 05, 2026

import os
import tempfile

import pytest

from src.utils.security.auth_service import AuthService
from src.utils.security.config import SecurityConfig
from src.utils.security.hasher import PBKDF2PasswordHasher
from src.utils.security.lockdown import FileLockdownManager, InMemoryLockdownManager
from src.utils.security.user_repository import InMemoryUserRepository, JsonUserRepository
from src.utils.security.user_service import UserManagementService
from src.utils.security_manager import SecurityManager


def test_hasher_pbkdf2_generates_unique_salts_and_verifies():
    hasher = PBKDF2PasswordHasher(iterations=1000)
    pwd = "MySecretPassword123!"

    hash1 = hasher.hash_password(pwd)
    hash2 = hasher.hash_password(pwd)

    # Different salts should yield different strings
    assert hash1 != hash2
    # But both must successfully verify
    assert hasher.verify_password(pwd, hash1) is True
    assert hasher.verify_password(pwd, hash2) is True
    # Wrong password must fail
    assert hasher.verify_password("WrongPassword", hash1) is False
    # Malformed hash must safely return False
    assert hasher.verify_password(pwd, "invalid_format") is False


def test_in_memory_lockdown_manager():
    lockdown = InMemoryLockdownManager()
    assert lockdown.is_active() is False

    lockdown.activate()
    assert lockdown.is_active() is True

    lockdown.clear()
    assert lockdown.is_active() is False


def test_file_lockdown_manager():
    with tempfile.TemporaryDirectory() as tmp_dir:
        flag_path = os.path.join(tmp_dir, "test_lockdown.flag")
        lockdown = FileLockdownManager(flag_path)

        assert lockdown.is_active() is False
        lockdown.activate()
        assert lockdown.is_active() is True
        assert os.path.exists(flag_path)

        lockdown.clear()
        assert lockdown.is_active() is False
        assert not os.path.exists(flag_path)


def test_in_memory_user_repository():
    repo = InMemoryUserRepository()
    assert repo.list_users() == []

    repo.set_user("alice", "hash_alice", "OPERATOR")
    repo.set_user("bob", "hash_bob", "SUPERUSER")

    assert repo.get_user("alice") == {"hash": "hash_alice", "role": "OPERATOR"}
    assert len(repo.list_users()) == 2

    assert repo.delete_user("alice") is True
    assert repo.get_user("alice") is None
    assert len(repo.list_users()) == 1

    # Counter tests
    assert repo.get_failed_attempts() == 0
    assert repo.increment_failed_attempts() == 1
    assert repo.increment_failed_attempts() == 2
    repo.reset_failed_attempts()
    assert repo.get_failed_attempts() == 0


def test_security_manager_orchestration_with_pure_in_memory_mocks():
    """
    Demonstrates Dependency Inversion Principle (DIP):
    SecurityManager runs 100% in-memory with custom mocks without touching filesystem.
    """
    hasher = PBKDF2PasswordHasher(iterations=1000)
    lockdown_mgr = InMemoryLockdownManager()
    user_repo = InMemoryUserRepository()

    config = SecurityConfig(
        security_file="in_memory_sec.json",
        lockdown_file="in_memory_lockdown.flag",
        is_production=False,
        master_user="admin",
        master_hash=hasher.hash_password("admin"),
        max_failed_attempts=3,
    )

    sm = SecurityManager(config=config, hasher=hasher, lockdown_mgr=lockdown_mgr, user_repo=user_repo)

    # Register normal operator and superuser
    assert sm.add_user("operator1", "OpPass123!", "OPERATOR") is True
    assert sm.add_user("superuser1", "SuPass123!", "SUPERUSER") is True

    # 1. Successful authentication
    success, role = sm.authenticate("operator1", "OpPass123!")
    assert success is True
    assert role == "OPERATOR"

    # 2. Failed attempts trigger lockdown after 3 tries
    assert sm.is_lockdown() is False
    sm.authenticate("operator1", "WrongPass1")
    sm.authenticate("operator1", "WrongPass2")
    assert sm.is_lockdown() is False

    sm.authenticate("operator1", "WrongPass3")
    assert sm.is_lockdown() is True

    # 3. During lockdown, regular operator cannot log in
    success_locked, msg = sm.authenticate("operator1", "OpPass123!")
    assert success_locked is False
    assert "LOCKED" in msg

    # 4. SuperUser logs in during lockdown and clears it
    success_su, role_su = sm.authenticate("superuser1", "SuPass123!")
    assert success_su is True
    assert role_su == "SUPERUSER"
    assert sm.is_lockdown() is False

    # 5. User deletion
    assert sm.remove_user("operator1") is True
    user_names = [u["username"] for u in sm.list_users()]
    assert "operator1" not in user_names
    assert "admin" in user_names
    assert "superuser1" in user_names
    assert len(sm.list_users()) == 2


def test_auth_service_standalone():
    hasher = PBKDF2PasswordHasher(iterations=1000)
    user_repo = InMemoryUserRepository({"alice": {"hash": hasher.hash_password("Secret123!"), "role": "OPERATOR"}})
    lockdown_mgr = InMemoryLockdownManager()
    config = SecurityConfig(
        security_file="sec.json",
        lockdown_file="lock.flag",
        is_production=True,
        master_user="master_root",
        master_hash="some_hash",
        max_failed_attempts=2,
    )

    auth = AuthService(config, user_repo, hasher, lockdown_mgr)

    # In production, admin:admin is blocked
    success, msg = auth.authenticate("admin", "admin")
    assert success is False

    # Valid user authenticate
    success, role = auth.authenticate("alice", "Secret123!")
    assert success is True
    assert role == "OPERATOR"

    # Failed attempts
    auth.authenticate("alice", "wrong")
    assert lockdown_mgr.is_active() is False
    auth.authenticate("alice", "wrong2")
    assert lockdown_mgr.is_active() is True


def test_user_management_service_standalone():
    hasher = PBKDF2PasswordHasher(iterations=1000)
    user_repo = InMemoryUserRepository()
    config = SecurityConfig(
        security_file="sec.json",
        lockdown_file="lock.flag",
        is_production=True,
        master_user="master_admin",
        master_hash="hash",
        max_failed_attempts=3,
    )

    user_svc = UserManagementService(config, user_repo, hasher)

    # In production, password 'admin' is rejected
    assert user_svc.add_user("test", "admin", "OPERATOR") is False

    # Invalid role rejected
    assert user_svc.add_user("test", "StrongPass1!", "INVALID_ROLE") is False

    # Valid add
    assert user_svc.add_user("test", "StrongPass1!", "OPERATOR") is True

    # Master user deletion is protected
    assert user_svc.remove_user("master_admin") is False
    assert user_svc.remove_user("test") is True
