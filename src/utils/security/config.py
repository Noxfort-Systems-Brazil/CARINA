# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: src/utils/security/config.py
# Author: Gabriel Moraes
# Date: September 05, 2026

import hashlib
import os
from dataclasses import dataclass
from typing import Optional

try:
    from utils.paths import get_base_output_dir, get_user_config_dir
except ImportError:
    from src.utils.paths import get_base_output_dir, get_user_config_dir


@dataclass
class SecurityConfig:
    """
    Encapsulates security paths, environment-based configuration, and credentials.
    Adheres to the 12-Factor App methodology for config isolation.
    """

    security_file: str
    lockdown_file: str
    is_production: bool
    master_user: str
    master_hash: str
    max_failed_attempts: int = 3

    @classmethod
    def load_from_env(
        cls, security_file: Optional[str] = None, lockdown_file: Optional[str] = None, max_failed_attempts: int = 3
    ) -> "SecurityConfig":
        """Factory method that loads configuration from environment variables and .env."""
        cls._load_env_file()

        user_config_dir = get_user_config_dir()
        resolved_security_file = security_file or os.path.join(user_config_dir, "security.json")
        resolved_lockdown_file = lockdown_file or os.path.join(user_config_dir, "lockdown.flag")

        env_name = os.getenv("CARINA_ENV", "").strip().lower()
        env_su_user = os.getenv("CARINA_SUPERUSER_USER", os.getenv("CARINA_MASTER_USER", "")).strip()
        env_su_hash = os.getenv("CARINA_SUPERUSER_HASH", os.getenv("CARINA_MASTER_HASH", "")).strip()
        env_su_pwd = os.getenv("CARINA_SUPERUSER_PASSWORD", os.getenv("CARINA_MASTER_PASSWORD", "")).strip()

        is_production = (
            env_name == "production"
            or (bool(env_su_user) and env_su_user != "admin")
            or bool(env_su_hash or env_su_pwd)
        )

        if env_su_pwd:
            env_su_hash = hashlib.sha256(env_su_pwd.encode("utf-8")).hexdigest()

        if env_su_user and env_su_hash:
            master_user = env_su_user
            master_hash = env_su_hash
        else:
            master_user = "admin"
            master_hash = hashlib.sha256("admin".encode("utf-8")).hexdigest()

        return cls(
            security_file=resolved_security_file,
            lockdown_file=resolved_lockdown_file,
            is_production=is_production,
            master_user=master_user,
            master_hash=master_hash,
            max_failed_attempts=max_failed_attempts,
        )

    @staticmethod
    def _load_env_file() -> None:
        """Loads environment variables from local .env if present."""
        try:
            from dotenv import load_dotenv

            load_dotenv()
        except ImportError:
            pass

        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
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
