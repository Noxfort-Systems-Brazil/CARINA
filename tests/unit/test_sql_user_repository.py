# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import sqlite3
import pytest
from src.security.sql_user_repo import SqlUserRepository


class MockSQLiteEngine:
    def __init__(self, db_path=":memory:"):
        self.db_type = "sqlite"
        self.is_shared_connection = True
        self._conn = sqlite3.connect(db_path)

    def get_connection(self):
        return self._conn


def test_sql_user_repository_ensure_default_user():
    engine = MockSQLiteEngine()
    repo = SqlUserRepository(engine=engine)

    repo.ensure_default_user(is_production=False, master_user="admin", default_hash="mock_admin_hash")
    user = repo.get_user("admin")

    assert user is not None
    assert user["hash"] == "mock_admin_hash"
    assert user["role"] == "SUPERUSER"


def test_sql_user_repository_crud():
    engine = MockSQLiteEngine()
    repo = SqlUserRepository(engine=engine)

    # Insert new user -> returns False (was not update)
    is_update = repo.set_user("operator_1", "hash_abc", "OPERATOR")
    assert is_update is False

    user = repo.get_user("operator_1")
    assert user is not None
    assert user["hash"] == "hash_abc"
    assert user["role"] == "OPERATOR"

    # Update existing user -> returns True
    is_update = repo.set_user("operator_1", "hash_new", "SUPERUSER")
    assert is_update is True

    user = repo.get_user("operator_1")
    assert user["hash"] == "hash_new"
    assert user["role"] == "SUPERUSER"

    # List users
    repo.set_user("admin", "hash_admin", "SUPERUSER")
    users = repo.list_users()
    usernames = [u["username"] for u in users]
    assert "admin" in usernames
    assert "operator_1" in usernames

    # Delete user
    assert repo.delete_user("operator_1") is True
    assert repo.get_user("operator_1") is None
    assert repo.delete_user("operator_1") is False


def test_sql_user_repository_failed_attempts():
    engine = MockSQLiteEngine()
    repo = SqlUserRepository(engine=engine)

    assert repo.get_failed_attempts() == 0

    assert repo.increment_failed_attempts() == 1
    assert repo.increment_failed_attempts() == 2
    assert repo.get_failed_attempts() == 2

    repo.reset_failed_attempts()
    assert repo.get_failed_attempts() == 0
