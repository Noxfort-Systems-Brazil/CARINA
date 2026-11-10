# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Unit tests for src/repositories/cloud_vault_repo.py
"""

import os
import tempfile
from unittest.mock import MagicMock, patch
import pytest

from src.repositories.cloud_vault_repo import CloudVaultRepository


class TestCloudVaultRepository:
    @pytest.fixture
    def mock_locale(self):
        lm = MagicMock()
        lm.get_string.side_effect = lambda k, default=None, **kw: default or k
        return lm

    def test_sync_file_to_vault_size_limit(self, mock_locale):
        engine = MagicMock()
        repo = CloudVaultRepository(engine, mock_locale)

        with tempfile.NamedTemporaryFile() as tmp:
            with patch("os.path.getsize", return_value=60 * 1024 * 1024):
                assert repo.sync_file_to_vault(tmp.name, "/tmp") is False

    def test_sync_file_to_vault_sqlite_and_postgres(self, mock_locale):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"hello vault")
            tmp.flush()
            filepath = tmp.name

        try:
            # 1. SQLite path
            engine_sqlite = MagicMock()
            engine_sqlite.db_type = "sqlite"
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            engine_sqlite.get_connection.return_value = mock_conn

            repo_sq = CloudVaultRepository(engine_sqlite, mock_locale)
            assert repo_sq.sync_file_to_vault(filepath, os.path.dirname(filepath)) is True
            assert mock_cursor.execute.called
            assert mock_conn.commit.called

            # 2. Postgres path
            engine_pg = MagicMock()
            engine_pg.db_type = "postgres"
            mock_conn_pg = MagicMock()
            mock_cursor_pg = MagicMock()
            mock_conn_pg.cursor.return_value = mock_cursor_pg
            engine_pg.get_connection.return_value = mock_conn_pg

            repo_pg = CloudVaultRepository(engine_pg, mock_locale)
            assert repo_pg.sync_file_to_vault(filepath, os.path.dirname(filepath)) is True
            assert mock_cursor_pg.execute.called
            assert mock_conn_pg.commit.called

            # 3. Connection is None
            engine_none = MagicMock()
            engine_none.get_connection.return_value = None
            repo_none = CloudVaultRepository(engine_none, mock_locale)
            assert repo_none.sync_file_to_vault(filepath, os.path.dirname(filepath)) is False
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)

    def test_sync_all_files_to_vault(self, mock_locale):
        with tempfile.TemporaryDirectory() as tmp_dir:
            f1 = os.path.join(tmp_dir, "test.txt")
            f_db = os.path.join(tmp_dir, "carina.db")
            f_journal = os.path.join(tmp_dir, "carina.db-journal")

            with open(f1, "w") as f:
                f.write("data")
            with open(f_db, "w") as f:
                f.write("db")
            with open(f_journal, "w") as f:
                f.write("journal")

            engine = MagicMock()
            repo = CloudVaultRepository(engine, mock_locale)

            with patch.object(repo, "sync_file_to_vault", return_value=True) as mock_sync:
                repo.sync_all_files_to_vault(tmp_dir)
                # Only test.txt should be synced
                assert mock_sync.call_count == 1

    def test_fetch_and_restore_file_from_vault(self, mock_locale):
        engine = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        engine.get_connection.return_value = mock_conn

        repo = CloudVaultRepository(engine, mock_locale)

        # 1. Row found
        mock_cursor.fetchone.return_value = [b"binary data content"]
        content = repo.fetch_file_from_vault("model.pth")
        assert content == b"binary data content"

        # 2. Row not found
        mock_cursor.fetchone.return_value = None
        assert repo.fetch_file_from_vault("missing.pth") is None

        # 3. Restore to disk
        with tempfile.TemporaryDirectory() as tmp_dir:
            target = os.path.join(tmp_dir, "restored.pth")
            mock_cursor.fetchone.return_value = [b"file payload"]
            assert repo.restore_file_from_vault("model.pth", target) is True
            assert os.path.exists(target)
            with open(target, "rb") as f:
                assert f.read() == b"file payload"

            # 4. Restore missing file
            mock_cursor.fetchone.return_value = None
            assert repo.restore_file_from_vault("bad.pth", target) is False

    def test_restore_all_files_from_vault(self, mock_locale):
        with tempfile.TemporaryDirectory() as tmp_dir:
            engine = MagicMock()
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = [
                ("models/a.pth", b"model A"),
                ("models/b.pth", b"model B"),
                ("bad_entry", None),
            ]
            mock_conn.cursor.return_value = mock_cursor
            engine.get_connection.return_value = mock_conn

            repo = CloudVaultRepository(engine, mock_locale)
            count = repo.restore_all_files_from_vault(tmp_dir)
            assert count == 2
            assert os.path.exists(os.path.join(tmp_dir, "models", "a.pth"))
            assert os.path.exists(os.path.join(tmp_dir, "models", "b.pth"))
