# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
JSON User Repository Component (SOLID: SRP & DIP).
Encapsulates atomic local file-based identity persistence for Edge operation.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from src.security.interfaces import IUserRepository

logger = logging.getLogger("JsonUserRepository")


class JsonUserRepository(IUserRepository):
    """
    JSON file-based implementation of IUserRepository.
    Provides fast, local offline-first identity storage for edge nodes.
    """

    def __init__(self, security_file: str, locale_manager: Optional[object] = None):
        self.security_file = security_file
        self.locale_manager = locale_manager

    def _get_string(self, key: str, default: str = "", **kwargs) -> str:
        if self.locale_manager and hasattr(self.locale_manager, "get_string"):
            try:
                res = self.locale_manager.get_string(key, default=default, **kwargs)
                return res
            except TypeError:
                res = self.locale_manager.get_string(key, default=default)
                if kwargs and isinstance(res, str):
                    try:
                        return res.format(**kwargs)
                    except Exception:
                        pass
                return res
        return default.format(**kwargs) if default and kwargs else (default or key)

    def _load_db(self) -> Dict[str, Any]:
        """Loads and returns the security database dictionary."""
        if not os.path.exists(self.security_file):
            return {"users": {}, "failed_attempts": 0}
        try:
            with open(self.security_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(
                self._get_string(
                    "security_manager.read_db_error",
                    default=f"[SecurityManager] Error reading security database: {e}",
                    error=e,
                )
            , exc_info=True)
            return {"users": {}, "failed_attempts": 0}

    def _save_db(self, db: Dict[str, Any]) -> None:
        """Saves the security database dictionary to JSON."""
        try:
            os.makedirs(os.path.dirname(self.security_file), exist_ok=True)
            with open(self.security_file, "w", encoding="utf-8") as f:
                json.dump(db, f, indent=4)
        except Exception as e:
            logger.error(
                self._get_string(
                    "security_manager.save_db_error",
                    default=f"[SecurityManager] Error saving security database: {e}",
                    error=e,
                )
            , exc_info=True)

    # --- Modern IUserRepository Contracts ---

    def ensure_storage(self) -> None:
        """Ensures the storage directory and file exist."""
        os.makedirs(os.path.dirname(self.security_file), exist_ok=True)
        if not os.path.exists(self.security_file):
            self._save_db({"users": {}, "failed_attempts": 0})

    def fetch_users(self) -> Dict[str, Dict[str, str]]:
        """Loads all registered users mapping username -> {'hash': ..., 'role': ...}."""
        db = self._load_db()
        return dict(db.get("users", {}))

    def save_user(self, username: str, password_hash: str, role: str) -> bool:
        """Persists or updates a user credential record."""
        db = self._load_db()
        users = db.setdefault("users", {})
        users[username] = {"hash": password_hash, "role": role}
        self._save_db(db)
        return True

    def delete_user(self, username: str) -> bool:
        """Deletes a user record by username."""
        db = self._load_db()
        users = db.get("users", {})
        if username in users:
            del users[username]
            self._save_db(db)
            return True
        return False

    # --- Backward-Compatibility Contracts for CARINA Legacy Callers ---

    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        db = self._load_db()
        return db.get("users", {}).get(username)

    def set_user(self, username: str, password_hash: str, role: str) -> bool:
        db = self._load_db()
        users = db.setdefault("users", {})
        is_update = username in users
        users[username] = {"hash": password_hash, "role": role}
        self._save_db(db)
        return is_update

    def list_users(self) -> List[Dict[str, Any]]:
        db = self._load_db()
        return [{"username": u, "role": data.get("role", "OPERATOR")} for u, data in db.get("users", {}).items()]

    def get_failed_attempts(self) -> int:
        db = self._load_db()
        return int(db.get("failed_attempts", 0))

    def increment_failed_attempts(self) -> int:
        db = self._load_db()
        count = int(db.get("failed_attempts", 0)) + 1
        db["failed_attempts"] = count
        self._save_db(db)
        return count

    def reset_failed_attempts(self) -> None:
        db = self._load_db()
        db["failed_attempts"] = 0
        self._save_db(db)

    def ensure_default_user(self, is_production: bool, master_user: str, default_hash: str) -> None:
        os.makedirs(os.path.dirname(self.security_file), exist_ok=True)
        if not os.path.exists(self.security_file):
            if is_production and master_user != "admin":
                default_db = {"users": {}, "failed_attempts": 0}
            else:
                default_db = {"users": {"admin": {"hash": default_hash, "role": "SUPERUSER"}}, "failed_attempts": 0}
            self._save_db(default_db)
            logger.info(
                self._get_string(
                    "security_manager.default_user_created", default="[SecurityManager] Security database initialized."
                )
            )


class InMemoryUserRepository(IUserRepository):
    """
    Volatile in-memory implementation for tests and mocking.
    """

    def __init__(self, initial_users: Optional[Dict[str, Dict[str, str]]] = None):
        self._users: Dict[str, Dict[str, str]] = initial_users.copy() if initial_users else {}
        self._failed_attempts: int = 0

    def ensure_storage(self) -> None:
        pass

    def fetch_users(self) -> Dict[str, Dict[str, str]]:
        return self._users.copy()

    def save_user(self, username: str, password_hash: str, role: str) -> bool:
        self._users[username] = {"hash": password_hash, "role": role}
        return True

    def delete_user(self, username: str) -> bool:
        if username in self._users:
            del self._users[username]
            return True
        return False

    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        return self._users.get(username)

    def set_user(self, username: str, password_hash: str, role: str) -> bool:
        is_update = username in self._users
        self._users[username] = {"hash": password_hash, "role": role}
        return is_update

    def list_users(self) -> List[Dict[str, Any]]:
        return [{"username": u, "role": data.get("role", "OPERATOR")} for u, data in self._users.items()]

    def get_failed_attempts(self) -> int:
        return self._failed_attempts

    def increment_failed_attempts(self) -> int:
        self._failed_attempts += 1
        return self._failed_attempts

    def reset_failed_attempts(self) -> None:
        self._failed_attempts = 0

    def ensure_default_user(self, is_production: bool, master_user: str, default_hash: str) -> None:
        if not self._users:
            if not (is_production and master_user != "admin"):
                self._users["admin"] = {"hash": default_hash, "role": "SUPERUSER"}
