# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import sqlite3
from typing import TYPE_CHECKING, Any, Optional

from src.database.db_config import DatabaseConfig
from src.database.schema_initializer import DatabaseSchemaInitializer
from src.database.sqlite_wrappers import SQLiteConnectionWrapper, SQLiteCursorWrapper

if TYPE_CHECKING:
    from src.utils.locale_manager_backend import LocaleManagerBackend


class DatabaseEngine:
    """
    Central engine and facade for managing database connections (SQLite or PostgreSQL).
    Delegates configuration loading to DatabaseConfig and schema initialization to DatabaseSchemaInitializer.
    """

    def __init__(
        self, locale_manager: "LocaleManagerBackend", db_name: str = "carina_data.db", run_migrations: bool = False
    ):
        self.locale_manager = locale_manager
        self._fatal_db_error = False
        self.run_migrations = run_migrations

        # Load centralized configuration
        cfg = DatabaseConfig(db_name=db_name)
        self.config = cfg.config
        self.db_type = cfg.db_type
        self.db_connected = cfg.db_connected
        self.db_host = cfg.db_host
        self.db_port = cfg.db_port
        self.db_user = cfg.db_user
        self.db_password = cfg.db_password
        self.db_name_pg = cfg.db_name_pg
        self.db_schema = cfg.db_schema
        self.db_path = cfg.db_path

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
                return sqlite3.connect(self.db_path, factory=SQLiteConnectionWrapper)
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
                logging.error(f"[DB_ENGINE] Failed to connect to the database ({self.db_type}): {e}", exc_info=True)
            return None

    def _load_schema_config(self) -> dict:
        return DatabaseSchemaInitializer.load_schema_config()

    def apply_migrations(self, db_url: Optional[str] = None) -> bool:
        """Applies pending Alembic database migrations up to 'head'."""
        return DatabaseSchemaInitializer.apply_migrations(self, db_url=db_url)

    def _initialize_db(self) -> None:
        """Creates the necessary tables, migrations, and indexes in the database dynamically."""
        DatabaseSchemaInitializer.initialize_db(self)
