# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Hybrid Composite User Repository (SOLID: SRP, OCP, ISP & DIP).
Provides Offline-First Edge Resilience for Smart City operations by coordinating
local cache with central database persistence.
"""

import logging
from typing import Any, Dict, List, Optional

from src.security.interfaces import ISynchronizable, IUserRepository

logger = logging.getLogger("HybridUserRepository")


class HybridUserRepository(IUserRepository, ISynchronizable):
    """
    Composite Repository coordinating local offline cache and remote central database.
    Depends exclusively on IUserRepository abstractions (DIP).
    """

    def __init__(
        self,
        local_repo: IUserRepository,
        remote_repo: Optional[IUserRepository] = None,
    ):
        self.local_repo = local_repo
        self.remote_repo = remote_repo

    def _is_remote_available(self) -> bool:
        if not self.remote_repo:
            return False
        if hasattr(self.remote_repo, "is_available"):
            return bool(self.remote_repo.is_available())
        return True

    def ensure_storage(self) -> None:
        """Ensures local storage and remote database table exist, then triggers sync."""
        self.local_repo.ensure_storage()
        if self._is_remote_available() and self.remote_repo:
            self.remote_repo.ensure_storage()
            self.sync()

    def sync(self) -> None:
        """
        Reconciles users between local cache and central database:
        - Restores users from DB to local file if missing locally.
        - Pushes users created locally while offline up to central DB.
        """
        if not self._is_remote_available() or not self.remote_repo:
            return

        try:
            self.remote_repo.ensure_storage()
            db_users = self.remote_repo.fetch_users()
            local_users = self.local_repo.fetch_users()

            modified_local = False
            for uname, udata in db_users.items():
                if uname not in local_users:
                    self.local_repo.save_user(uname, udata.get("hash", ""), udata.get("role", "OPERATOR"))
                    modified_local = True

            for uname, udata in local_users.items():
                if uname not in db_users:
                    self.remote_repo.save_user(uname, udata.get("hash", ""), udata.get("role", "OPERATOR"))

            if modified_local:
                logger.info(
                    f"[HybridUserRepository] Restored {len(db_users)} user(s) from central database to local security file."
                )
        except Exception as e:
            logger.debug(f"[HybridUserRepository] User sync skipped (offline or uninitialized): {e}")

    def fetch_users(self) -> Dict[str, Dict[str, str]]:
        """Returns users from local edge cache."""
        return self.local_repo.fetch_users()

    def save_user(self, username: str, password_hash: str, role: str) -> bool:
        """Saves user locally and attempts remote sync."""
        local_saved = self.local_repo.save_user(username, password_hash, role)
        if self._is_remote_available() and self.remote_repo:
            try:
                self.remote_repo.save_user(username, password_hash, role)
            except Exception as e:
                logger.warning(f"[HybridUserRepository] Remote save user failed (will sync later): {e}", exc_info=True)
        return local_saved

    def delete_user(self, username: str) -> bool:
        """Deletes user from both local cache and remote database."""
        local_deleted = self.local_repo.delete_user(username)
        remote_deleted = False
        if self._is_remote_available() and self.remote_repo:
            try:
                remote_deleted = self.remote_repo.delete_user(username)
            except Exception as e:
                logger.warning(f"[HybridUserRepository] Remote delete user failed: {e}", exc_info=True)
        return local_deleted or remote_deleted

    # --- Backward compatibility methods ---

    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        if hasattr(self.local_repo, "get_user"):
            return self.local_repo.get_user(username)
        users = self.fetch_users()
        return users.get(username)

    def set_user(self, username: str, password_hash: str, role: str) -> bool:
        return self.save_user(username, password_hash, role)

    def list_users(self) -> List[Dict[str, Any]]:
        if hasattr(self.local_repo, "list_users"):
            return self.local_repo.list_users()
        users = self.fetch_users()
        return [{"username": u, "role": d.get("role", "OPERATOR")} for u, d in users.items()]

    def get_failed_attempts(self) -> int:
        if hasattr(self.local_repo, "get_failed_attempts"):
            return self.local_repo.get_failed_attempts()
        return 0

    def increment_failed_attempts(self) -> int:
        if hasattr(self.local_repo, "increment_failed_attempts"):
            return self.local_repo.increment_failed_attempts()
        return 1

    def reset_failed_attempts(self) -> None:
        if hasattr(self.local_repo, "reset_failed_attempts"):
            self.local_repo.reset_failed_attempts()

    def ensure_default_user(self, is_production: bool, master_user: str, default_hash: str) -> None:
        if hasattr(self.local_repo, "ensure_default_user"):
            self.local_repo.ensure_default_user(is_production, master_user, default_hash)
        else:
            self.ensure_storage()
