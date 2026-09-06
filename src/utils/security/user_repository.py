# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: src/utils/security/user_repository.py
# Author: Gabriel Moraes
# Date: September 05, 2026

import json
import logging
import os
from typing import Any, Optional

from src.utils.security.interfaces import IUserRepository


class JsonUserRepository(IUserRepository):
    """
    JSON file-based implementation of IUserRepository.
    Encapsulates database I/O, serialization, and failed attempts persistence.
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

    def _load_db(self) -> dict[str, Any]:
        """Loads and returns the security database dictionary."""
        try:
            with open(self.security_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(
                self._get_string(
                    "security_manager.read_db_error",
                    default="[SecurityManager] Error reading security database: {error}",
                    error=e,
                )
            )
            return {"users": {}, "failed_attempts": 0}

    def _save_db(self, db: dict[str, Any]) -> None:
        """Saves the security database dictionary to JSON."""
        try:
            os.makedirs(os.path.dirname(self.security_file), exist_ok=True)
            with open(self.security_file, "w", encoding="utf-8") as f:
                json.dump(db, f, indent=4)
        except Exception as e:
            logging.error(
                self._get_string(
                    "security_manager.save_db_error",
                    default="[SecurityManager] Error saving security database: {error}",
                    error=e,
                )
            )

    def ensure_default_user(self, is_production: bool, master_user: str, default_hash: str) -> None:
        """Initializes default database structure if security.json does not exist."""
        os.makedirs(os.path.dirname(self.security_file), exist_ok=True)
        if not os.path.exists(self.security_file):
            if is_production and master_user != "admin":
                default_db = {"users": {}, "failed_attempts": 0}
            else:
                default_db = {"users": {"admin": {"hash": default_hash, "role": "SUPERUSER"}}, "failed_attempts": 0}
            self._save_db(default_db)
            logging.info(
                self._get_string(
                    "security_manager.default_user_created", default="[SecurityManager] Security database initialized."
                )
            )

    def get_user(self, username: str) -> Optional[dict[str, Any]]:
        db = self._load_db()
        return db.get("users", {}).get(username)

    def set_user(self, username: str, password_hash: str, role: str) -> bool:
        db = self._load_db()
        users = db.setdefault("users", {})
        is_update = username in users
        users[username] = {"hash": password_hash, "role": role}
        self._save_db(db)
        return is_update

    def delete_user(self, username: str) -> bool:
        db = self._load_db()
        users = db.get("users", {})
        if username in users:
            del users[username]
            self._save_db(db)
            return True
        return False

    def list_users(self) -> list[dict[str, Any]]:
        db = self._load_db()
        return [{"username": uname, "role": data["role"]} for uname, data in db.get("users", {}).items()]

    def get_failed_attempts(self) -> int:
        db = self._load_db()
        return db.get("failed_attempts", 0)

    def increment_failed_attempts(self) -> int:
        db = self._load_db()
        count = db.get("failed_attempts", 0) + 1
        db["failed_attempts"] = count
        self._save_db(db)
        return count

    def reset_failed_attempts(self) -> None:
        db = self._load_db()
        if db.get("failed_attempts", 0) > 0:
            db["failed_attempts"] = 0
            self._save_db(db)


class InMemoryUserRepository(IUserRepository):
    """
    In-memory implementation of IUserRepository for fast, isolated unit testing.
    """

    def __init__(self, initial_users: Optional[dict[str, Any]] = None, failed_attempts: int = 0):
        self.users = initial_users or {}
        self.failed_attempts = failed_attempts

    def ensure_default_user(self, is_production: bool, master_user: str, default_hash: str) -> None:
        if not self.users:
            if not (is_production and master_user != "admin"):
                self.users["admin"] = {"hash": default_hash, "role": "SUPERUSER"}

    def get_user(self, username: str) -> Optional[dict[str, Any]]:
        return self.users.get(username)

    def set_user(self, username: str, password_hash: str, role: str) -> bool:
        is_update = username in self.users
        self.users[username] = {"hash": password_hash, "role": role}
        return is_update

    def delete_user(self, username: str) -> bool:
        if username in self.users:
            del self.users[username]
            return True
        return False

    def list_users(self) -> list[dict[str, Any]]:
        return [{"username": uname, "role": data["role"]} for uname, data in self.users.items()]

    def get_failed_attempts(self) -> int:
        return self.failed_attempts

    def increment_failed_attempts(self) -> int:
        self.failed_attempts += 1
        return self.failed_attempts

    def reset_failed_attempts(self) -> None:
        self.failed_attempts = 0
