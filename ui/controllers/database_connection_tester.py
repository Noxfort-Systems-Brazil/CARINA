# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import sqlite3
import threading
from typing import Callable, Tuple

from src.utils.paths import get_base_output_dir


class DatabaseConnectionTester:
    """
    Asynchronous connection testing service for SQLite and PostgreSQL databases.
    Decouples raw DB socket/driver access from UI components (Clean Architecture / SRP).
    """

    @staticmethod
    def test_connection_sync(
        db_type: str,
        host: str = "localhost",
        port: str = "5432",
        user: str = "postgres",
        password: str = "",
        dbname: str = "carina_data",
    ) -> Tuple[bool, str]:
        """Performs a synchronous test query on the target database."""
        conn = None
        cursor = None
        try:
            if db_type == "sqlite":
                db_dir = os.path.join(get_base_output_dir(), "results", "database")
                os.makedirs(db_dir, exist_ok=True)
                db_path = os.path.join(db_dir, dbname if dbname.endswith(".db") else f"{dbname}.db")

                conn = sqlite3.connect(db_path, timeout=10.0)
                conn.execute("SELECT 1")
                return True, ""

            elif db_type == "postgres":
                import psycopg2

                conn = psycopg2.connect(
                    host=host,
                    port=port,
                    user=user,
                    password=password,
                    dbname=dbname,
                    connect_timeout=5,
                )
                cursor = conn.cursor()
                cursor.execute("SELECT 1;")
                return True, ""
            else:
                return False, f"Unknown database type: {db_type}"
        except Exception as e:
            return False, str(e)
        finally:
            if cursor is not None:
                try:
                    cursor.close()
                except Exception:
                    pass
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass

    @staticmethod
    def test_connection_async(
        db_type: str,
        host: str,
        port: str,
        user: str,
        password: str,
        dbname: str,
        callback: Callable[[bool, str], None],
    ) -> None:
        """Runs the connection test in a daemon background thread and invokes callback."""

        def _worker():
            success, err_msg = DatabaseConnectionTester.test_connection_sync(
                db_type=db_type, host=host, port=port, user=user, password=password, dbname=dbname
            )
            callback(success, err_msg)

        threading.Thread(target=_worker, daemon=True).start()
