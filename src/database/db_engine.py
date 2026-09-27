# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# File: src/database/db_engine.py
# Author: Gabriel Moraes
# Date: May 31, 2026

import configparser
import json
import logging
import os
import sqlite3
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from src.utils.locale_manager_backend import LocaleManagerBackend


class DatabaseEngine:
    """
    Central engine for managing database connections (SQLite or PostgreSQL).
    Responsible for connecting, initializing the schema dynamically from config/database/schema_queries.json,
    and providing active database connections.
    """

    def __init__(self, locale_manager: "LocaleManagerBackend", db_name: str = "carina_data.db"):
        self.locale_manager = locale_manager
        self._fatal_db_error = False

        project_root_local = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

        # 12-Factor App: Load environment variables from .env if present
        try:
            from dotenv import load_dotenv

            load_dotenv()
        except ImportError:
            pass

        env_file_path = os.path.join(project_root_local, ".env")
        if os.path.isfile(env_file_path):
            try:
                with open(env_file_path, "r", encoding="utf-8") as f:
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

        # Parse settings directly
        self.config = configparser.ConfigParser()
        settings_path = os.path.join(project_root_local, "config", "settings.ini")
        if os.path.exists(settings_path):
            self.config.read(settings_path)

        self.db_type = os.getenv("CARINA_DB_TYPE", self.config.get("DATABASE", "db_type", fallback="sqlite"))
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

        self._initialize_db()
        logging.info(f"[DB_ENGINE] Central Engine Initialized. DB: {self.db_type}")

    def get_connection(self) -> Any:
        """Returns a connection (psycopg2 or sqlite3) depending on the configuration."""
        if getattr(self, "_fatal_db_error", False):
            return None

        try:
            if self.db_type == "postgres":
                import psycopg2

                return psycopg2.connect(
                    host=self.db_host,
                    port=self.db_port,
                    user=self.db_user,
                    password=self.db_password,
                    dbname=self.db_name_pg,
                    options=f"-c search_path={self.db_schema},public",
                )
            else:
                return sqlite3.connect(self.db_path)
        except Exception as e:
            error_msg = str(e).lower()
            if "password authentication failed" in error_msg or "fatal:" in error_msg or "fe_sendauth" in error_msg:
                self._fatal_db_error = True
                logging.critical(
                    f"[DB_ENGINE] CRITICAL: Fatal PostgreSQL connection error for user '{self.db_user}' / db '{self.db_name_pg}'. Connection disabled to prevent spam. Details: {e}"
                )
                print(f"\n[CARINA FATAL ERROR] Invalid database credentials or database does not exist.")
                print(
                    f"User: '{self.db_user}', DB: '{self.db_name_pg}'. Please update your settings and restart the application.\n"
                )
            else:
                logging.error(f"[DB_ENGINE] Failed to connect to the database ({self.db_type}): {e}")
            return None

    def _load_schema_config(self) -> dict:
        try:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            candidates = [
                os.path.join(base_dir, "config", "database", "schema_queries.json"),
                os.path.join(base_dir, "config", "schema_queries.json"),
            ]
            for json_path in candidates:
                if os.path.exists(json_path):
                    with open(json_path, "r", encoding="utf-8") as f:
                        return json.load(f)
        except Exception as e:
            logging.error(f"[DB_ENGINE] Failed to load schema_queries.json: {e}")
        return {}

    def apply_migrations(self, db_url: Optional[str] = None) -> bool:
        """Applies pending Alembic database migrations up to 'head'."""
        try:
            from alembic import command
            from alembic.config import Config

            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            alembic_ini_path = os.path.join(project_root, "alembic.ini")
            if not os.path.exists(alembic_ini_path):
                return False
            alembic_cfg = Config(alembic_ini_path)
            if not db_url:
                if self.db_type == "sqlite" and self.db_path:
                    db_url = f"sqlite:///{os.path.abspath(self.db_path)}"
                elif self.db_type == "postgres" and hasattr(self, "db_host") and self.db_host:
                    db_url = (
                        f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
                    )
            if db_url:
                alembic_cfg.set_main_option("sqlalchemy.url", db_url)
            command.upgrade(alembic_cfg, "head")
            logging.info("[DB_ENGINE] Alembic migrations successfully applied to 'head'.")
            return True
        except Exception as e:
            logging.warning(f"[DB_ENGINE] Alembic migration skipped or failed: {e}")
            return False

    def _initialize_db(self):
        """
        Creates the necessary tables, migrations, and indexes in the database dynamically.
        Uses Alembic migrations as primary mechanism, with schema_queries.json as fallback.
        """
        conn = self.get_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()

            # 0. Ensure PostgreSQL schema exists and search_path is explicitly routed
            if self.db_type == "postgres":
                safe_schema = "".join(c for c in self.db_schema if c.isalnum() or c == "_") or "schema_carina"
                cursor.execute(f'CREATE SCHEMA IF NOT EXISTS "{safe_schema}";')
                cursor.execute(f'SET search_path TO "{safe_schema}", public;')
                conn.commit()

            # Try Alembic migration first if sqlite or postgres URL is available
            migration_applied = False
            try:
                migration_applied = self.apply_migrations()
            except Exception:
                migration_applied = False

            schema_config = self._load_schema_config()
            dialect_config = schema_config.get(self.db_type, schema_config.get("sqlite", {}))

            for table_sql in dialect_config.get("tables", []):
                try:
                    cursor.execute(table_sql)
                    conn.commit()
                except Exception:
                    pass

            # 2. Migrations
            migrations = dialect_config.get("migrations", [])
            if self.db_type == "postgres":
                cursor.execute(
                    """
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = 'synapse_fluid_dynamics'
                      AND table_schema = CURRENT_SCHEMA;
                """
                )
                existing_cols = {row[0] for row in cursor.fetchall()}
                for m in migrations:
                    if isinstance(m, dict) and m.get("column") not in existing_cols:
                        try:
                            cursor.execute(m["sql"])
                            conn.commit()
                        except Exception:
                            pass
            else:
                for migration_sql in migrations:
                    sql_stmt = migration_sql if isinstance(migration_sql, str) else migration_sql.get("sql")
                    try:
                        cursor.execute(sql_stmt)
                        conn.commit()
                    except Exception:
                        pass

            # 3. Create Indexes
            for index_sql in dialect_config.get("indexes", []):
                cursor.execute(index_sql)
                conn.commit()

        except Exception as e:
            if conn:
                conn.rollback()
            logging.error(f"[DB_ENGINE] Error during _initialize_db: {e}")
            try:
                logging.error(self.locale_manager.get_string("db_manager.init.db_error", error=e))
            except Exception:
                pass
        finally:
            if conn:
                conn.close()
