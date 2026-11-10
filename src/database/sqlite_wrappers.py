# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import sqlite3
from typing import Any


class SQLiteCursorWrapper(sqlite3.Cursor):
    """Wraps sqlite3.Cursor to provide PEP 249 context manager support and Postgres syntax compatibility."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def execute(self, sql: str, parameters: Any = None):
        if isinstance(sql, str):
            if "BIGSERIAL PRIMARY KEY" in sql:
                sql = sql.replace("BIGSERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT")
            if "%s" in sql and parameters is not None:
                sql = sql.replace("%s", "?")
        if parameters is not None:
            return super().execute(sql, parameters)
        return super().execute(sql)

    def executemany(self, sql: str, seq_of_parameters: Any):
        if isinstance(sql, str) and "%s" in sql:
            sql = sql.replace("%s", "?")
        return super().executemany(sql, seq_of_parameters)


class SQLiteConnectionWrapper(sqlite3.Connection):
    """Wraps sqlite3.Connection to return context-manager compatible cursors."""

    def cursor(self, *args, **kwargs) -> SQLiteCursorWrapper:
        return super().cursor(factory=SQLiteCursorWrapper)
