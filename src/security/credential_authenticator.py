# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Credential Authenticator (Clean Architecture / SOLID: SRP).
Encapsulates user account lookup, password verification, and production security rules.
"""

import logging
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger("CredentialAuthenticator")


class CredentialAuthenticator:
    """
    Application component dedicated to looking up registered users,
    verifying password hashes, and enforcing production credentials restrictions.
    """

    def __init__(
        self,
        user_repository: Any,
        hasher: Any,
        db_engine: Optional[Any] = None,
        sync_callback: Optional[Callable[[], None]] = None,
        is_production: bool = False,
        default_dev_password: str = "Admin@Carina2026!",
    ):
        self.user_repository = user_repository
        self.hasher = hasher
        self.db_engine = db_engine
        self.sync_callback = sync_callback
        self.is_production = is_production
        self.default_dev_password = default_dev_password

    def fetch_users_map(self) -> Dict[str, Dict[str, str]]:
        """Resolves the username to user data dictionary safely."""
        users: Dict[str, Dict[str, str]] = {}
        if hasattr(self.user_repository, "fetch_users"):
            users = self.user_repository.fetch_users()
        elif hasattr(self.user_repository, "list_users"):
            for u_item in self.user_repository.list_users():
                uname = u_item.get("username")
                if uname and hasattr(self.user_repository, "get_user"):
                    u_data = self.user_repository.get_user(uname)
                    if u_data:
                        users[uname] = u_data
        return users

    def get_user_data(self, username: str, users: Dict[str, Dict[str, str]]) -> Optional[Dict[str, str]]:
        """Retrieves user profile data from repository or cached dictionary."""
        user_data = None
        if hasattr(self.user_repository, "get_user"):
            user_data = self.user_repository.get_user(username)
        if not user_data and username in users:
            user_data = users[username]
        return user_data

    def sync_if_needed(self, username: str, users: Dict[str, Dict[str, str]]) -> Dict[str, Dict[str, str]]:
        """Performs database synchronization if the user is missing and engine is attached."""
        if username not in users and self.db_engine:
            if self.sync_callback:
                try:
                    self.sync_callback()
                except Exception as e:
                    logger.debug(f"[CredentialAuthenticator] Sync callback failed: {e}")
            elif hasattr(self.user_repository, "sync"):
                try:
                    self.user_repository.sync()
                except Exception as e:
                    logger.debug(f"[CredentialAuthenticator] Repo sync failed: {e}")
            return self.fetch_users_map()
        return users

    def verify_superuser_unlock(
        self, username: str, password: str, users: Dict[str, Dict[str, str]]
    ) -> bool:
        """Checks if the user is an authorized SUPERUSER able to unlock system from lockdown."""
        users = self.sync_if_needed(username, users)
        user_data = self.get_user_data(username, users)
        if user_data and user_data.get("role") == "SUPERUSER":
            return bool(self.hasher.verify_password(password, user_data.get("hash", "")))
        return False

    def verify_credentials(
        self, username: str, password: str, users: Dict[str, Dict[str, str]]
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validates user credentials against stored hash and production security constraints.
        Returns (success: bool, role_or_None: Optional[str], fail_reason_or_None: Optional[str]).
        """
        users = self.sync_if_needed(username, users)
        user_data = self.get_user_data(username, users)

        if not user_data:
            return False, None, "User not found"

        # Production security check for default admin credentials
        if (
            self.is_production
            and username == "admin"
            and (
                self.hasher.verify_password("admin", user_data.get("hash", ""))
                or self.hasher.verify_password(self.default_dev_password, user_data.get("hash", ""))
            )
        ):
            logger.warning("[CredentialAuthenticator] Insecure default 'admin' account credentials blocked in production.")
            return False, None, "Admin default password rejected"

        if self.hasher.verify_password(password, user_data.get("hash", "")):
            role = user_data.get("role", "OPERATOR")
            return True, role, None

        return False, None, "Wrong password"
