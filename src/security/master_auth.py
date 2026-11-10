# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Master & Emergency Credential Verification Component (SOLID: SRP).
Decouples emergency god-mode authentication from standard user lifecycles.
"""

import hashlib
from typing import Any, Optional, Tuple


class MasterCredentialValidator:
    """
    Validates master and default emergency credentials using SHA-256 digests.
    Enforces strict production safety rules against insecure demo accounts.
    """

    def __init__(
        self,
        master_user: str,
        master_hash: str,
        default_user: str = "admin",
        default_hash: str = "",
        is_production: bool = False,
        hasher: Optional[Any] = None,
    ):
        self.master_user = master_user
        self.master_hash = master_hash
        self.default_user = default_user
        self.default_hash = default_hash
        self.is_production = is_production
        self.hasher = hasher

    def is_protected_master(self, username: str) -> bool:
        """Returns True if the username matches any protected system identity."""
        return username in (self.master_user, self.default_user)

    def is_insecure_default_blocked(self, username: str, password: str) -> bool:
        """
        In production, blocks default test/demo credentials ('admin').
        """
        if not self.is_production:
            return False

        if username == "admin":
            if password in ("admin", "Admin@Carina2026!"):
                return True
        return False

    def verify_master(self, username: str, password: str) -> Tuple[bool, bool]:
        """
        Verifies credentials against master identities.
        Returns:
            (is_authenticated_master, is_master_attempt)
            - is_authenticated_master: True if username matches master and hash matches.
            - is_master_attempt: True if username matches master regardless of password.
        """
        if not self.is_protected_master(username):
            return False, False

        # In production, block demo admin account immediately
        if self.is_insecure_default_blocked(username, password):
            return False, True

        raw_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()

        if username == self.master_user and raw_hash == self.master_hash:
            return True, True

        if self.default_hash and username == self.default_user and raw_hash == self.default_hash:
            return True, True

        return False, True
