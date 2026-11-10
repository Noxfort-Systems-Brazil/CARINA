# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Unit Tests for Refactored SOLID Security Subsystem Components (src/security/).
Tests FileLockdownManager, AttemptStores, MasterCredentialValidator,
HybridUserRepository, AuditLogger, and Dependency Injection on SecurityManager.
"""

import os
import shutil
import tempfile
import pytest

from src.security.account_manager import UserAccountManager
from src.security.attempt_store import JsonAttemptStore, MemoryAttemptStore
from src.security.audit_logger import AuditLogger
from src.security.config import SecurityConfig
from src.security.crypto import Pbkdf2PasswordHasher, Sha256Hasher
from src.security.hybrid_user_repo import HybridUserRepository
from src.security.interfaces import (
    IAttemptCounterStore,
    ILockdownManager,
    ISynchronizable,
    IUserRepository,
)
from src.security.json_user_repo import InMemoryUserRepository
from src.security.lockdown_manager import FileLockdownManager, InMemoryLockdownManager
from src.security.master_auth import MasterCredentialValidator
from src.security.models import AuthResult, User, UserRole
from src.security.password_policy import ModernPasswordPolicy
from src.security.security_manager import SecurityManager


@pytest.fixture
def temp_dir():
    d = tempfile.mkdtemp(prefix="carina_solid_test_")
    yield d
    if os.path.exists(d):
        shutil.rmtree(d, ignore_errors=True)


def test_attempt_counter_stores(temp_dir):
    """Validates segregated attempt stores (JSON and Memory)."""
    # JsonAttemptStore
    sec_file = os.path.join(temp_dir, "security.json")
    json_store = JsonAttemptStore(sec_file)
    assert isinstance(json_store, IAttemptCounterStore)
    assert json_store.get_failed_attempts() == 0
    json_store.set_failed_attempts(4)
    assert json_store.get_failed_attempts() == 4

    # MemoryAttemptStore
    mem_store = MemoryAttemptStore(initial_count=2)
    assert isinstance(mem_store, IAttemptCounterStore)
    assert mem_store.get_failed_attempts() == 2
    mem_store.set_failed_attempts(0)
    assert mem_store.get_failed_attempts() == 0


def test_file_lockdown_manager(temp_dir):
    """Validates FileLockdownManager rate-limiting and threshold trigger."""
    flag_path = os.path.join(temp_dir, "lockdown.flag")
    attempts = [0]

    lockdown = FileLockdownManager(
        lockdown_file=flag_path,
        max_failed_attempts=2,
        attempts_getter=lambda: attempts[0],
        attempts_setter=lambda val: attempts.__setitem__(0, val),
    )
    assert isinstance(lockdown, ILockdownManager)
    assert lockdown.is_lockdown() is False

    # Attempt 1: not triggered
    assert lockdown.record_failed_attempt() is False
    assert lockdown.is_lockdown() is False
    assert attempts[0] == 1

    # Attempt 2: threshold reached -> triggers lockdown
    assert lockdown.record_failed_attempt() is True
    assert lockdown.is_lockdown() is True
    assert os.path.isfile(flag_path)
    assert attempts[0] == 2

    # Clear lockdown
    lockdown.clear_lockdown()
    assert lockdown.is_lockdown() is False
    assert not os.path.exists(flag_path)
    assert attempts[0] == 0


def test_master_credential_validator():
    """Validates decoupled master credential authentication."""
    hasher = Pbkdf2PasswordHasher(iterations=1000)
    master_hash = Sha256Hasher.hash_password("SuperSecretMaster2026!")

    validator = MasterCredentialValidator(
        master_user="traffic_chief",
        master_hash=master_hash,
        default_user="admin",
        is_production=True,
    )

    # In production, default admin is blocked
    is_master, is_attempt = validator.verify_master("admin", "admin")
    assert is_master is False
    assert is_attempt is True

    # Real master authenticated
    is_master, is_attempt = validator.verify_master("traffic_chief", "SuperSecretMaster2026!")
    assert is_master is True
    assert is_attempt is True

    # Unknown user
    is_master, is_attempt = validator.verify_master("random_user", "some_pass")
    assert is_master is False
    assert is_attempt is False


def test_hybrid_user_repository():
    """Validates Composite Hybrid Repository offline-first reconciliation."""
    local_repo = InMemoryUserRepository({"local_user": {"hash": "h_local", "role": "OPERATOR"}})
    remote_repo = InMemoryUserRepository({"remote_user": {"hash": "h_remote", "role": "SUPERUSER"}})

    hybrid = HybridUserRepository(local_repo=local_repo, remote_repo=remote_repo)
    assert isinstance(hybrid, IUserRepository)
    assert isinstance(hybrid, ISynchronizable)

    # Initial sync: remote_user is reconciled into local cache
    hybrid.sync()
    users = hybrid.fetch_users()
    assert "local_user" in users
    assert "remote_user" in users

    # Save user propagates to both
    assert hybrid.save_user("field_engineer", "hash_fe", "SUPERUSER") is True
    assert "field_engineer" in local_repo.fetch_users()
    assert "field_engineer" in remote_repo.fetch_users()

    # Delete propagates to both
    assert hybrid.delete_user("field_engineer") is True
    assert "field_engineer" not in local_repo.fetch_users()
    assert "field_engineer" not in remote_repo.fetch_users()


def test_audit_logger(temp_dir):
    """Validates structured dual-persistence audit logging and chronological order."""
    audit = AuditLogger(config_dir=temp_dir)
    audit.log_action("operator_1", "UPDATE_SIGNAL_PHASE", "Intersection 42 switched to Phase 3")
    audit.log_action("operator_2", "TRIGGER_LOCKDOWN", "Emergency security test")

    logs = audit.get_logs(limit=10)
    assert len(logs) == 2
    # Newest log first
    assert logs[0]["action"] == "TRIGGER_LOCKDOWN"
    assert logs[0]["username"] == "operator_2"
    assert logs[1]["action"] == "UPDATE_SIGNAL_PHASE"
    assert logs[1]["username"] == "operator_1"


def test_security_manager_solid_in_memory_orchestration():
    """
    Demonstrates strict Dependency Inversion Principle (DIP):
    Orchestrates the entire Security Subsystem 100% in-memory without filesystem I/O.
    """
    hasher = Pbkdf2PasswordHasher(iterations=1000)
    lockdown_mgr = InMemoryLockdownManager(max_failed_attempts=2)
    user_repo = InMemoryUserRepository()
    attempt_store = MemoryAttemptStore()
    policy = ModernPasswordPolicy()

    sec_mgr = SecurityManager(
        hasher=hasher,
        lockdown_manager=lockdown_mgr,
        user_repository=user_repo,
        attempt_store=attempt_store,
        password_policy=policy,
        is_production=False,
    )

    # 1. Register users via in-memory Account Manager
    sec_mgr.account_manager.create_user("traffic_operator", "TrafficOp2026!", UserRole.OPERATOR)
    sec_mgr.account_manager.create_user("traffic_admin", "Admin2026!Secured", UserRole.SUPERUSER)

    # 2. Authenticate Valid Operator
    res = sec_mgr.authenticator.authenticate_user("traffic_operator", "TrafficOp2026!")
    assert res.success is True
    assert res.user.role == UserRole.OPERATOR

    # 3. Simulate brute-force -> Lockdown
    assert sec_mgr.authenticator.authenticate("traffic_operator", "WrongPass1")[0] is False
    assert sec_mgr.authenticator.authenticate("traffic_operator", "WrongPass2")[0] is False
    assert sec_mgr.authenticator.is_lockdown() is True

    # 4. Standard operator cannot authenticate during lockdown
    locked_res = sec_mgr.authenticator.authenticate_user("traffic_operator", "TrafficOp2026!")
    assert locked_res.success is False

    # 5. SUPERUSER unlocks lockdown
    super_res = sec_mgr.authenticator.authenticate_user("traffic_admin", "Admin2026!Secured")
    assert super_res.success is True
    assert super_res.user.role == UserRole.SUPERUSER
    assert sec_mgr.authenticator.is_lockdown() is False
