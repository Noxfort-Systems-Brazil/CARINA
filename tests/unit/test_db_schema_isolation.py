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

# File: tests/unit/test_db_schema_isolation.py
# Author: Gabriel Moraes
# Date: September 2026

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

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
