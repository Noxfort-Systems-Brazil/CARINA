# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Security Configuration Component (SOLID: SRP).
Encapsulates security paths, environment-based configuration, and credentials
following the 12-Factor App methodology.
"""

import hashlib
import os
from dataclasses import dataclass
from typing import ClassVar, Optional

from src.utils.paths import get_base_output_dir, get_user_config_dir


@dataclass
class SecurityConfig:
    """
    Encapsulates security paths, environment-based configuration, and credentials.
    """

    DEFAULT_DEV_USER: ClassVar[str] = "admin"
    DEFAULT_DEV_PASSWORD: ClassVar[str] = "Admin@Carina2026!"

    security_file: str
    lockdown_file: str
    is_production: bool
    master_user: str
    master_hash: str
    max_failed_attempts: int = 3
    secret_key: Optional[str] = None
    user_storage: str = "auto"
    config_dir: Optional[str] = None
    default_user: str = "admin"
    default_hash: str = ""

    def __post_init__(self):
        if not self.default_hash:
            self.default_hash = hashlib.sha256(self.DEFAULT_DEV_PASSWORD.encode("utf-8")).hexdigest()
        if not self.config_dir:
            self.config_dir = os.path.dirname(self.security_file)

    @classmethod
    def load_from_env(
        cls,
        security_file: Optional[str] = None,
        lockdown_file: Optional[str] = None,
        max_failed_attempts: int = 3,
        config_dir: Optional[str] = None,
    ) -> "SecurityConfig":
        """Factory method that loads configuration from environment variables and .env."""
        cls._load_env_file()

        resolved_config_dir = config_dir or get_user_config_dir()
        resolved_security_file = security_file or os.path.join(resolved_config_dir, "security.json")
        resolved_lockdown_file = lockdown_file or os.path.join(resolved_config_dir, "lockdown.flag")

        env_name = os.getenv("CARINA_ENV", "").strip().lower()
        env_su_user = os.getenv("CARINA_SUPERUSER_USER", os.getenv("CARINA_MASTER_USER", "")).strip()
        env_su_hash = os.getenv("CARINA_SUPERUSER_HASH", os.getenv("CARINA_MASTER_HASH", "")).strip()
        env_su_pwd = os.getenv("CARINA_SUPERUSER_PASSWORD", os.getenv("CARINA_MASTER_PASSWORD", "")).strip()

        is_production = (
            env_name == "production"
            or (
                env_name != "development"
                and (
                    (bool(env_su_user) and env_su_user != cls.DEFAULT_DEV_USER)
                    or bool(env_su_hash or env_su_pwd)
                )
            )
        )

        if env_su_pwd:
            env_su_hash = hashlib.sha256(env_su_pwd.encode("utf-8")).hexdigest()

        default_dev_hash = hashlib.sha256(cls.DEFAULT_DEV_PASSWORD.encode("utf-8")).hexdigest()

        if env_su_user and env_su_hash:
            master_user = env_su_user
            master_hash = env_su_hash
        else:
            master_user = cls.DEFAULT_DEV_USER
            master_hash = default_dev_hash

        secret_key = os.getenv("CARINA_SECRET_KEY", "").strip() or None
        user_storage = os.getenv("CARINA_USER_STORAGE", "auto").strip().lower()

        return cls(
            security_file=resolved_security_file,
            lockdown_file=resolved_lockdown_file,
            is_production=is_production,
            master_user=master_user,
            master_hash=master_hash,
            max_failed_attempts=max_failed_attempts,
            secret_key=secret_key,
            user_storage=user_storage,
            config_dir=resolved_config_dir,
            default_user=cls.DEFAULT_DEV_USER,
            default_hash=default_dev_hash,
        )

    @classmethod
    def from_env(
        cls,
        security_file: Optional[str] = None,
        lockdown_file: Optional[str] = None,
        max_failed_attempts: int = 3,
        config_dir: Optional[str] = None,
    ) -> "SecurityConfig":
        """Alias for load_from_env to align with SYNAPSE_CORE naming."""
        return cls.load_from_env(
            security_file=security_file,
            lockdown_file=lockdown_file,
            max_failed_attempts=max_failed_attempts,
            config_dir=config_dir,
        )

    @staticmethod
    def _load_env_file() -> None:
        """Loads environment variables from local .env if present."""
        try:
            from dotenv import load_dotenv

            load_dotenv()
        except ImportError:
            pass

        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        env_path = os.path.join(project_root, ".env")
        if os.path.isfile(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k and k not in os.environ:
                            os.environ[k] = v
            except Exception:
                pass
