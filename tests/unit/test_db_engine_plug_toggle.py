# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import sqlite3
from unittest.mock import MagicMock, patch

import pytest
from src.database.db_engine import DatabaseEngine


def test_db_engine_defaults_to_sqlite_when_postgres_unplugged(tmp_path):
    """
    Verifies that when db_type is 'postgres' but db_connected is 'False',
    DatabaseEngine safely falls back to local SQLite and does NOT attempt
    to connect to PostgreSQL.
    """
    mock_lm = MagicMock()
    test_db_name = "test_toggle_disconnected.db"

    with patch.dict(os.environ, {"CARINA_DB_TYPE": "postgres", "CARINA_DB_CONNECTED": "False"}):
        with patch.object(DatabaseEngine, "_initialize_db"):
            engine = DatabaseEngine(locale_manager=mock_lm, db_name=test_db_name)

            assert engine.db_connected is False
            assert engine.db_type == "sqlite"

            conn = engine.get_connection()
            assert isinstance(conn, sqlite3.Connection)
            conn.close()


def test_db_engine_activates_postgres_when_explicitly_plugged(tmp_path):
    """
    Verifies that when db_type is 'postgres' and db_connected is 'True',
    DatabaseEngine acknowledges postgres as active and attempts PostgreSQL connection.
    """
    mock_lm = MagicMock()
    test_db_name = "test_toggle_connected.db"

    with patch.dict(os.environ, {"CARINA_DB_TYPE": "postgres", "CARINA_DB_CONNECTED": "True"}):
        with patch.object(DatabaseEngine, "_initialize_db"):
            engine = DatabaseEngine(locale_manager=mock_lm, db_name=test_db_name)

            assert engine.db_connected is True
            assert engine.db_type == "postgres"

            with patch("psycopg2.connect") as mock_pg_conn:
                mock_pg_conn.return_value = MagicMock()
                conn = engine.get_connection()
                assert conn is not None
                mock_pg_conn.assert_called_once()


def test_db_engine_default_settings_ini(tmp_path):
    """
    Verifies that with clean environment variables (reading settings.ini directly),
    the current settings.ini defaults to disconnected / sqlite.
    """
    mock_lm = MagicMock()
    test_db_name = "test_clean_defaults.db"

    clean_env = {k: v for k, v in os.environ.items() if not k.startswith("CARINA_DB_")}
    with patch.dict(os.environ, clean_env, clear=True):
        with patch.object(DatabaseEngine, "_initialize_db"):
            engine = DatabaseEngine(locale_manager=mock_lm, db_name=test_db_name)

            assert engine.db_connected is False
            assert engine.db_type == "sqlite"
