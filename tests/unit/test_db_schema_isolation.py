# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from unittest.mock import MagicMock, patch

import pytest

from src.database.db_engine import DatabaseEngine


def test_db_engine_initializes_postgres_schema():
    mock_locale = MagicMock()

    with patch.object(DatabaseEngine, "_initialize_db"):
        engine = DatabaseEngine(mock_locale)
        engine.db_type = "postgres"
        engine.db_schema = "schema_carina"

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []

    with patch.object(engine, "get_connection", return_value=mock_conn):
        DatabaseEngine._initialize_db(engine)

    # Verify CREATE SCHEMA IF NOT EXISTS and SET search_path were executed
    executed_sqls = [call[0][0] for call in mock_cursor.execute.call_args_list if call[0]]

    assert any('CREATE SCHEMA IF NOT EXISTS "schema_carina";' in sql for sql in executed_sqls)
    assert any('SET search_path TO "schema_carina", public;' in sql for sql in executed_sqls)
    assert mock_conn.commit.called


def test_db_engine_sanitizes_schema_name():
    mock_locale = MagicMock()

    with patch.object(DatabaseEngine, "_initialize_db"):
        engine = DatabaseEngine(mock_locale)
        engine.db_type = "postgres"
        engine.db_schema = "malicious_schema; DROP TABLE students; --"

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []

    with patch.object(engine, "get_connection", return_value=mock_conn):
        DatabaseEngine._initialize_db(engine)

    executed_sqls = [call[0][0] for call in mock_cursor.execute.call_args_list if call[0]]
    assert any('CREATE SCHEMA IF NOT EXISTS "malicious_schemaDROPTABLEstudents";' in sql for sql in executed_sqls)


def test_db_engine_sqlite_does_not_create_schema():
    mock_locale = MagicMock()

    with patch.object(DatabaseEngine, "_initialize_db"):
        engine = DatabaseEngine(mock_locale)
        engine.db_type = "sqlite"

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    with patch.object(engine, "get_connection", return_value=mock_conn):
        DatabaseEngine._initialize_db(engine)

    executed_sqls = [call[0][0] for call in mock_cursor.execute.call_args_list if call[0]]
    assert not any("CREATE SCHEMA" in sql for sql in executed_sqls)
