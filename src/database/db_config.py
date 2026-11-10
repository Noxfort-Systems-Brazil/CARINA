# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import configparser
import logging
import os
from typing import Optional


class DatabaseConfig:
    """Encapsulates multi-source configuration loading (.env, settings.ini, env vars) for database connections."""

    def __init__(self, db_name: str = "carina_data.db"):
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

        # 12-Factor App: Load environment variables from .env if present
        try:
            from dotenv import load_dotenv

            load_dotenv()
        except ImportError:
            pass

        env_file_path = os.path.join(self.project_root, ".env")
        if os.path.isfile(env_file_path):
            self._load_env_file(env_file_path)

        # Parse settings directly
        self.config = configparser.ConfigParser()
        settings_path = os.path.join(self.project_root, "config", "settings.ini")
        if os.path.exists(settings_path):
            self.config.read(settings_path)

        configured_db_type = os.getenv("CARINA_DB_TYPE", self.config.get("DATABASE", "db_type", fallback="sqlite"))
        db_connected_val = self.config.get("DATABASE", "db_connected", fallback="False")
        db_connected_raw = os.getenv("CARINA_DB_CONNECTED", db_connected_val)
        self.db_connected = str(db_connected_raw).strip().lower() in ("true", "1", "yes")

        # External database (PostgreSQL) is strictly opt-in and disabled by default until
        # explicitly connected/plugged (db_connected=True). Fallback to SQLite if disconnected.
        if configured_db_type == "postgres" and not self.db_connected:
            logging.info(
                "[DB_ENGINE] External database (PostgreSQL) is currently disconnected/disabled. Operating on local SQLite."
            )
            self.db_type = "sqlite"
        else:
            self.db_type = configured_db_type

        self.db_host = os.getenv("CARINA_DB_HOST", self.config.get("DATABASE", "db_host", fallback="localhost"))
        self.db_port = os.getenv("CARINA_DB_PORT", self.config.get("DATABASE", "db_port", fallback="5432"))
        self.db_user = os.getenv("CARINA_DB_USER", self.config.get("DATABASE", "db_user", fallback="admin"))
        self.db_password = os.getenv("CARINA_DB_PASSWORD", self.config.get("DATABASE", "db_password", fallback="admin"))
        self.db_name_pg = os.getenv("CARINA_DB_NAME", self.config.get("DATABASE", "db_name", fallback="carina_data"))
        self.db_schema = os.getenv(
            "CARINA_DB_SCHEMA", self.config.get("DATABASE", "db_schema", fallback="schema_carina")
        )

        # SQLite local path
        from src.utils.paths import get_base_output_dir

        db_dir = os.path.join(get_base_output_dir(), "results", "database")
        os.makedirs(db_dir, exist_ok=True)
        self.db_path = os.path.join(db_dir, db_name)

    @staticmethod
    def _load_env_file(filepath: str) -> None:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
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
