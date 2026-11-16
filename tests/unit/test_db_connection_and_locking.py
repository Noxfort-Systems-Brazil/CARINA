# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import sqlite3
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.database.connection_pool import PostgresConnectionPool
from src.database.database_manager import DatabaseManager
from src.database.db_engine import DatabaseEngine
from src.evp.evp_config_repo import EVPConfigRepository
from src.evp.evp_models import CorporationType, RegisteredVehicle
from src.repositories.operation_session_repo import OperationSessionRepository
from src.repositories.step_decision_analytics import StepDecisionAnalytics
from src.repositories.step_decision_repo import StepDecisionRepository
from src.repositories.topology_dictionary_repo import TopologyDictionaryRepository
from src.security.audit_logger import AuditLogger
from src.utils.locale_manager_backend import LocaleManagerBackend
from ui.controllers.database_connection_tester import DatabaseConnectionTester


class _TrackedCursor:
    def __init__(self, inner, stats, fail_on_execute=False):
        self._inner = inner
        self._stats = stats
        self._fail = fail_on_execute
        self._closed = False
        stats["cursor_opens"] += 1

    def execute(self, *args, **kwargs):
        if self._fail:
            raise RuntimeError("Simulated SQL failure")
        return self._inner.execute(*args, **kwargs)

    def executemany(self, *args, **kwargs):
        if self._fail:
            raise RuntimeError("Simulated SQL executemany failure")
        return self._inner.executemany(*args, **kwargs)

    def close(self):
        if not self._closed:
            self._closed = True
            self._stats["cursor_closes"] += 1
        return self._inner.close()

    def __getattr__(self, item):
        return getattr(self._inner, item)


class _TrackedConnection:
    def __init__(self, inner, stats, fail_on_execute=False):
        self._inner = inner
        self._stats = stats
        self._fail = fail_on_execute
        self._closed = False
        stats["conn_opens"] += 1

    def cursor(self, *args, **kwargs):
        return _TrackedCursor(self._inner.cursor(*args, **kwargs), self._stats, fail_on_execute=self._fail)

    def close(self):
        if not self._closed:
            self._closed = True
            self._stats["conn_closes"] += 1
        return self._inner.close()

    def __getattr__(self, item):
        return getattr(self._inner, item)


def test_sqlite_wal_and_concurrent_thread_stress_no_database_locked(tmp_path: Path):
    db_file = str(tmp_path / "wal_stress.db")
    locale = LocaleManagerBackend()
    mgr = DatabaseManager(locale, db_name=db_file)
    try:
        conn = mgr.engine.get_connection()
        try:
            mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
            busy = conn.execute("PRAGMA busy_timeout;").fetchone()[0]
            assert str(mode).lower() == "wal"
            assert int(busy) >= 30000
        finally:
            conn.close()

        step_repo = StepDecisionRepository(mgr.engine, locale)
        step_repo.ensure_tables_exist()
        topo_repo = TopologyDictionaryRepository(mgr.engine)
        sess_repo = OperationSessionRepository(mgr.engine)
        audit = AuditLogger(db_engine=mgr.engine, locale_manager=locale)
        evp_repo = EVPConfigRepository(engine=mgr.engine, locale_manager=locale)

        errors = []

        def _worker(tid: int):
            try:
                for step in range(15):
                    sid = sess_repo.start_session()
                    assert sid is not None
                    step_repo.increment_decision_counter_batch([(sid, tid % 4, step % 3)])
                    topo_repo.bulk_save_topology_elements(
                        [
                            {
                                "element_type": "edge",
                                "raw_net_id": f"e_{tid}_{step}",
                                "numeric_id": 10000 + tid * 100 + step,
                                "custom_name": f"Via {tid}-{step}",
                            }
                        ]
                    )
                    assert topo_repo.get_topology_custom_name("edge", f"e_{tid}_{step}") == f"Via {tid}-{step}"
                    audit.log_action(f"op_{tid}", "TEST_STRESS", f"step={step}")
                    evp_repo.save_vehicle(
                        RegisteredVehicle(vehicle_id=f"VTR-{tid}-{step}", corporation=CorporationType.SAMU)
                    )
                    _ = StepDecisionAnalytics.get_guardian_veto_statistics(mgr.engine, {0: "OK", 1: "VETO", 2: "CLAMP"})
                    assert sess_repo.end_session(sid) is True
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_worker, args=(i,)) for i in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=25.0)

        assert not errors, f"Unexpected DB lock/concurrency errors: {errors}"
        fleet = evp_repo.load_all_vehicles()
        assert len(fleet) == 8 * 15
    finally:
        mgr.close()


def test_repositories_and_tester_deterministically_close_connections_even_on_error(tmp_path: Path):
    db_file = str(tmp_path / "leak_audit.db")
    locale = LocaleManagerBackend()
    mgr = DatabaseManager(locale, db_name=db_file)
    try:
        StepDecisionRepository(mgr.engine, locale).ensure_tables_exist()
        stats = {"conn_opens": 0, "conn_closes": 0, "cursor_opens": 0, "cursor_closes": 0}
        real_get_conn = mgr.engine.get_connection
        fail_flag = {"fail": False}

        def _spy_get_connection():
            return _TrackedConnection(real_get_conn(), stats, fail_on_execute=fail_flag["fail"])

        with patch.object(mgr.engine, "get_connection", side_effect=_spy_get_connection):
            step_repo = StepDecisionRepository(mgr.engine, locale)
            topo_repo = TopologyDictionaryRepository(mgr.engine)
            sess_repo = OperationSessionRepository(mgr.engine)
            audit = AuditLogger(db_engine=mgr.engine, locale_manager=locale)
            evp_repo = EVPConfigRepository(engine=mgr.engine, locale_manager=locale)

            for i in range(10):
                sid = sess_repo.start_session()
                step_repo.increment_decision_counter_batch([(sid, 0, 1)])
                step_repo.get_all_audited_agent_ids()
                topo_repo.bulk_save_topology_elements(
                    [{"element_type": "tl", "raw_net_id": f"J{i}", "numeric_id": i + 1, "custom_name": f"Cruz {i}"}]
                )
                topo_repo.update_topology_custom_name("tl", f"J{i}", f"Av {i}")
                topo_repo.get_topology_custom_name("tl", f"J{i}")
                StepDecisionAnalytics.get_guardian_veto_statistics(mgr.engine, {0: "OK", 1: "VETO"})
                audit.log_action("tester", "PING", f"iter={i}")
                audit.get_logs(limit=5)
                evp_repo.save_vehicle(RegisteredVehicle(vehicle_id=f"AMB-{i}", corporation=CorporationType.SAMU))
                evp_repo.load_all_vehicles()
                sess_repo.end_session(sid)

            # Force SQL exceptions to confirm rollback/finally still closes every cursor & connection
            fail_flag["fail"] = True
            topo_repo.update_topology_custom_name("tl", "J0", "ERR")
            step_repo.get_all_audited_agent_ids()
            StepDecisionAnalytics.get_guardian_veto_statistics(mgr.engine, {0: "OK"})
            audit.log_action("tester", "FAIL_ERR", "detail")
            evp_repo.remove_vehicle("AMB-0")

        assert stats["conn_opens"] > 0
        assert stats["conn_closes"] == stats["conn_opens"], f"Connection leak: {stats}"
        assert stats["cursor_closes"] == stats["cursor_opens"], f"Cursor leak: {stats}"
    finally:
        mgr.close()


def test_database_connection_tester_closes_handles_on_error(tmp_path: Path):
    stats = {"conn_opens": 0, "conn_closes": 0, "cursor_opens": 0, "cursor_closes": 0}
    real_connect = sqlite3.connect

    def _tracked_sqlite_connect(*args, **kwargs):
        return _TrackedConnection(real_connect(*args, **kwargs), stats)

    with patch("ui.controllers.database_connection_tester.sqlite3.connect", side_effect=_tracked_sqlite_connect):
        ok, _msg = DatabaseConnectionTester.test_connection_sync("sqlite", dbname=str(tmp_path / "tester.db"))
    assert ok is True
    assert stats["conn_closes"] == stats["conn_opens"] == 1

    # Postgres test closes both cursor and connection even if execute() raises
    fake_cur = MagicMock()
    fake_cur.execute.side_effect = RuntimeError("PG query failure")
    fake_conn = MagicMock()
    fake_conn.cursor.return_value = fake_cur
    fake_psycopg2 = MagicMock()
    fake_psycopg2.connect.return_value = fake_conn

    with patch.dict("sys.modules", {"psycopg2": fake_psycopg2}):
        ok_pg, _msg_pg = DatabaseConnectionTester.test_connection_sync("postgres", dbname="carina_test")
    assert ok_pg is False
    fake_cur.close.assert_called_once()
    fake_conn.close.assert_called_once()


def test_postgres_connection_pool_lifecycle_and_database_manager_close(tmp_path: Path):
    fake_raw_conn = MagicMock()
    fake_raw_conn.closed = 0
    fake_pool = MagicMock()
    fake_pool.getconn.return_value = fake_raw_conn

    pool = PostgresConnectionPool(lambda: {"host": "localhost", "port": 5432}, minconn=1, maxconn=4)
    with patch("psycopg2.pool.ThreadedConnectionPool", return_value=fake_pool):
        proxy = pool.acquire()
        fake_raw_conn.rollback.assert_called()
        proxy.close()
        fake_pool.putconn.assert_called_once_with(fake_raw_conn, close=False)

        # Broken connection should pass close=True to putconn
        fake_pool.putconn.reset_mock()
        fake_raw_conn.closed = 1
        proxy2 = pool.acquire()
        proxy2.close()
        fake_pool.putconn.assert_called_once_with(fake_raw_conn, close=True)

        pool.close_all()
        fake_pool.closeall.assert_called_once()

    # Verify DatabaseManager.close delegates to engine.close()
    mgr = DatabaseManager(LocaleManagerBackend(), db_name=str(tmp_path / "close_check.db"))
    mgr.engine._pg_pool = fake_pool
    fake_pool.closeall.reset_mock()
    # Attach real close_all through PostgresConnectionPool wrapper
    pg_wrapper = PostgresConnectionPool(lambda: {})
    pg_wrapper._pool = fake_pool
    mgr.engine._pg_pool = pg_wrapper
    mgr.close()
    fake_pool.closeall.assert_called_once()
