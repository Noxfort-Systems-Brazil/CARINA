# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: ui/cards/database_connection_tester.py
# Author: Gabriel Moraes
# Date: September 2026

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
        try:
            if db_type == "sqlite":
                db_dir = os.path.join(get_base_output_dir(), "results", "database")
                os.makedirs(db_dir, exist_ok=True)
                db_path = os.path.join(db_dir, dbname if dbname.endswith(".db") else f"{dbname}.db")

                conn = sqlite3.connect(db_path)
                conn.execute("SELECT 1")
                conn.close()
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
                conn.close()
                return True, ""
            else:
                return False, f"Unknown database type: {db_type}"
        except Exception as e:
            return False, str(e)

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
