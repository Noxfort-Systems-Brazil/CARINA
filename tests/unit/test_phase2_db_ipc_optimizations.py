# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Regression tests for Phase 2 Database, Retention, Connection Pool, and IPC optimizations."""

import json
import os
import sqlite3
import threading
import time
from queue import Full
from unittest.mock import MagicMock

from src.communication.pipe_utils import ThreadSafePipeConnection, wrap_thread_safe_pipe
from src.database.connection_pool import _WAL_INITIALIZED_PATHS, configure_sqlite_connection
from src.database.database_manager import DatabaseManager
from src.evp.evp_models import CorporationType, EmergencyVehicle
from src.evp.evp_telemetry_repository import EVPTelemetryRepository
from src.handlers.ai_request_handler import AIRequestHandler
from src.repositories.cloud_vault_repo import CloudVaultRepository


def test_fluid_dynamics_queries_no_quoted_postgres_intervals():
    """PostgreSQL interval queries must never embed %s inside quotes."""
    qpath = os.path.join(os.getcwd(), "config", "database", "fluid_dynamics_queries.json")
    with open(qpath, "r", encoding="utf-8") as f:
        queries = json.load(f)

    for qname in ("purge_old", "get_min_collected_before", "get_cutoff_timestamp_interval", "get_next_batch_timestamp"):
        pg_sql = queries[qname]["postgres"]
        assert "'%s" not in pg_sql
        assert "make_interval" in pg_sql

    assert "scenario_name" in queries["consolidate_edge_summary"]["postgres"].split("ON CONFLICT", 1)[1]
    assert "scenario_name" in queries["consolidate_intersection_summary"]["postgres"].split("ON CONFLICT", 1)[1]


def test_sqlite_synchronous_normal_applied_per_connection(tmp_path):
    """PRAGMA synchronous=NORMAL (value 1) must apply to every new SQLite connection, not just connection #1."""
    db_path = str(tmp_path / "sync_check.db")
    _WAL_INITIALIZED_PATHS.discard(db_path)

    c1 = sqlite3.connect(db_path)
    c2 = sqlite3.connect(db_path)
    try:
        configure_sqlite_connection(c1, db_path)
        assert int(c1.execute("PRAGMA synchronous;").fetchone()[0]) == 1

        # Second connection hits cached WAL path, yet must STILL get synchronous = NORMAL (1)
        configure_sqlite_connection(c2, db_path)
        assert int(c2.execute("PRAGMA synchronous;").fetchone()[0]) == 1
    finally:
        c1.close()
        c2.close()
        _WAL_INITIALIZED_PATHS.discard(db_path)


def test_database_manager_disable_step_worker_and_evp_purge(tmp_path):
    """Read-only worker DatabaseManager skips spawning StepDecisionWorker and EVP retention purges old rows."""
    lm = MagicMock()
    db_file = str(tmp_path / "worker_mgr.db")
    mgr = DatabaseManager(lm, db_name=db_file, enable_step_worker=False)
    try:
        assert mgr.step_decision_worker is None

        evp_repo = EVPTelemetryRepository(mgr.engine, lambda c: c.close() if c else None)
        conn = mgr.engine.get_connection()
        try:
            conn.execute(
                """
                INSERT INTO evp_telemetry_records (
                    vehicle_id, corporation, latitude, longitude, speed_kmh, heading_deg, siren_active, created_at
                ) VALUES
                ('V_OLD', 'SAMU', -23.5, -46.6, 50.0, 90.0, 1, datetime('now', '-200 hours')),
                ('V_NEW', 'SAMU', -23.5, -46.6, 60.0, 90.0, 1, datetime('now', '-1 hours'));
                """
            )
            conn.commit()
        finally:
            conn.close()

        deleted = evp_repo.purge_old_telemetry(keep_hours=168)
        assert deleted == 1

        conn = mgr.engine.get_connection()
        try:
            remaining = [r[0] for r in conn.execute("SELECT vehicle_id FROM evp_telemetry_records;").fetchall()]
            assert remaining == ["V_NEW"]
        finally:
            conn.close()
    finally:
        mgr.close()


def test_cloud_vault_ignores_wal_shm_logs_and_unchanged_files(tmp_path):
    """CloudVaultRepository ignores SQLite WAL/SHM/logs and avoids re-uploading unmodified files."""
    for name in ("data.db", "data.db-wal", "data.db-shm", "app.log", "app.log.gz", "checkpoint.pth"):
        with open(tmp_path / name, "wb") as f:
            f.write(b"abc")

    lm = MagicMock()
    engine = MagicMock()
    repo = CloudVaultRepository(engine, lm)
    synced_files = []
    repo.sync_file_to_vault = lambda fp, bd: synced_files.append(os.path.basename(fp)) or True

    repo.sync_all_files_to_vault(str(tmp_path))
    assert synced_files == ["checkpoint.pth"]

    # Second pass without modification must skip checkpoint.pth
    repo.sync_all_files_to_vault(str(tmp_path))
    assert synced_files == ["checkpoint.pth"]


def test_thread_safe_pipe_connection_and_independent_queues():
    """ThreadSafePipeConnection serializes concurrent sends and AIRequestHandler isolates queue Full errors."""
    sent = []

    class _DummyConn:
        def __init__(self):
            self.active = 0
            self.overlap = False

        def send(self, obj):
            if self.active > 0:
                self.overlap = True
            self.active += 1
            time.sleep(0.002)
            sent.append(obj)
            self.active -= 1

    raw = _DummyConn()
    safe = wrap_thread_safe_pipe(raw)
    assert isinstance(safe, ThreadSafePipeConnection)
    assert wrap_thread_safe_pipe(safe) is safe

    threads = [threading.Thread(target=safe.send, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not raw.overlap
    assert sorted(sent) == list(range(10))

    # Full SAS queue must NOT prevent SDS delivery
    topo = MagicMock()
    topo.agent_maturity_cache = {}
    sds_q = MagicMock()
    sas_q = MagicMock()
    sas_q.put_nowait.side_effect = Full()
    handler = AIRequestHandler(
        locale_manager=MagicMock(),
        topology_manager=topo,
        sds_queue=sds_q,
        sas_queue=sas_q,
        health_monitor=MagicMock(),
        override_manager=MagicMock(),
    )
    handler.process(("ai_telemetry_sync", {"maturity": {"tl_1": "ADULT"}}), MagicMock(), MagicMock(), [])
    assert sds_q.put_nowait.called
