# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import sqlite3
from unittest.mock import MagicMock

import pytest

from repositories.fluid_dynamics_repo import FluidDynamicsRepository
from sas.analyzer_data_processor import AnalyzerDataProcessor


class MockDbEngine:
    def __init__(self):
        self.db_type = "sqlite"
        self._db_uri = f"file:memdb_{id(self)}?mode=memory&cache=shared"
        self._init_sqlite()

    def _init_sqlite(self):
        conn = sqlite3.connect(self._db_uri, uri=True)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS synapse_fluid_dynamics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                edge_id TEXT NOT NULL,
                density REAL,
                mean_speed REAL,
                min_speed REAL,
                queue_length REAL,
                max_queue REAL,
                occupancy REAL,
                edge_length REAL,
                num_lanes INTEGER,
                speed_limit REAL,
                maturity_stage TEXT DEFAULT 'CHILD',
                scenario_name TEXT DEFAULT 'default',
                intersection_id TEXT DEFAULT 'tl_1',
                collected_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """
        )
        # Insert test traffic samples for edge_A and edge_B
        cursor.execute(
            """
            INSERT INTO synapse_fluid_dynamics (edge_id, density, mean_speed, min_speed, queue_length, max_queue, occupancy, edge_length, num_lanes, speed_limit, maturity_stage, scenario_name, intersection_id, collected_at)
            VALUES
            ('edge_A', 10.0, 10.0, 5.0, 5, 10, 0.2, 100.0, 2, 13.89, 'CHILD', 'scen1', 'tl_1', '2026-08-01 06:00:00'),
            ('edge_A', 15.0, 8.0, 4.0, 8, 12, 0.3, 100.0, 2, 13.89, 'CHILD', 'scen1', 'tl_1', '2026-08-01 06:30:00'),
            ('edge_B', 5.0, 12.0, 8.0, 2, 5, 0.1, 150.0, 1, 13.89, 'CHILD', 'scen1', 'tl_1', '2026-08-01 07:00:00');
        """
        )
        conn.commit()
        # Keep one persistent connection open so the shared memory database doesn't disappear
        self._keepalive = conn

    def get_connection(self):
        return sqlite3.connect(self._db_uri, uri=True)


def test_fluid_dynamics_repo_pushdown_aggregation():
    engine = MockDbEngine()
    lm = MagicMock()
    repo = FluidDynamicsRepository(engine, lm)

    results = repo.query_aggregated_fluid_dynamics(limit_seconds=3600)
    assert len(results) == 3 or len(results) == 2

    edge_map = {row["edge_id"]: row for row in results}
    assert "edge_A" in edge_map
    assert "edge_B" in edge_map


def test_fluid_dynamics_min_max_timestamps():
    engine = MockDbEngine()
    lm = MagicMock()
    repo = FluidDynamicsRepository(engine, lm)

    min_dt, max_dt = repo.get_fluid_dynamics_min_max_timestamps()
    assert min_dt is not None
    assert max_dt is not None
    assert min_dt.strftime("%Y-%m-%d %H:%M:%S") == "2026-08-01 06:00:00"
    assert max_dt.strftime("%Y-%m-%d %H:%M:%S") == "2026-08-01 07:00:00"


def test_analyzer_data_processor_with_pushdown():
    engine = MockDbEngine()
    lm = MagicMock()

    class MockDbManager:
        def __init__(self):
            self.fluid_dynamics_repo = FluidDynamicsRepository(engine, lm)

        def query_aggregated_fluid_dynamics(self, limit_seconds=None):
            return self.fluid_dynamics_repo.query_aggregated_fluid_dynamics(limit_seconds)

        def query_fluid_dynamics_history_batches(self, limit_seconds=None, batch_size=50000):
            return self.fluid_dynamics_repo.query_fluid_dynamics_history_batches(limit_seconds, batch_size)

    mock_topology = MagicMock()
    mock_topology.build.return_value = (
        {"junction1": "traffic_light"},
        {"junction1": {"edge_A": {"num_lanes": 2}, "edge_B": {"num_lanes": 1}}},
    )

    processor = AnalyzerDataProcessor(locale_manager=lm, topology_parser=mock_topology)

    processed_data, true_tls = processor.process_historical_data(MockDbManager(), "mock_net.xml", limit_seconds=3600)

    assert true_tls == ["junction1"]
    assert "junction1" in processed_data
    assert len(processed_data["junction1"]["primary_edges"]) > 0


def test_query_fluid_dynamics_history_with_and_without_limit():
    engine = MockDbEngine()
    lm = MagicMock()
    repo = FluidDynamicsRepository(engine, lm)

    # With limit
    history_limited = repo.reader.query_fluid_dynamics_history(limit_seconds=3600)
    assert isinstance(history_limited, list)

    # Without limit (all)
    history_all = repo.reader.query_fluid_dynamics_history(limit_seconds=None)
    assert len(history_all) == 3
    assert history_all[0]["edge_id"] == "edge_A"


def test_query_fluid_dynamics_history_batches():
    engine = MockDbEngine()
    lm = MagicMock()
    repo = FluidDynamicsRepository(engine, lm)

    batches = list(repo.reader.query_fluid_dynamics_history_batches(limit_seconds=None, batch_size=2))
    assert len(batches) == 2
    assert len(batches[0]) == 2
    assert len(batches[1]) == 1


def test_fluid_dynamics_reader_fallbacks_and_connection_none():
    from src.repositories.fluid_dynamics_reader import FluidDynamicsReader

    engine = MagicMock()
    engine.get_connection.return_value = None
    query_provider = MagicMock()

    reader = FluidDynamicsReader(engine, query_provider, ["c1"], ["a1"])
    assert reader.query_fluid_dynamics_history() == []
    assert reader.query_aggregated_fluid_dynamics() == []
    assert list(reader.query_fluid_dynamics_history_batches()) == []

    # Test fallback branch when primary table is empty
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    # Primary returns empty, fallback returns rows
    mock_cursor.fetchall.side_effect = [[], [("edge_fallback",)]]
    mock_cursor.fetchmany.side_effect = [[], [("edge_fallback",)], []]
    mock_conn.cursor.return_value = mock_cursor
    engine.get_connection.return_value = mock_conn
    engine.db_type = "sqlite"

    res = reader.query_aggregated_fluid_dynamics(limit_seconds=None)
    assert len(res) == 1
    assert res[0]["a1"] == "edge_fallback"

    # Aggregated with limit_seconds fallback
    mock_cursor.fetchall.side_effect = [[], [("edge_fallback_limit",)]]
    res_lim = reader.query_aggregated_fluid_dynamics(limit_seconds=100)
    assert len(res_lim) == 1
    assert res_lim[0]["a1"] == "edge_fallback_limit"

    # Batches with limit_seconds fallback (postgres cursor)
    engine.db_type = "postgres"
    mock_cursor.fetchmany.side_effect = [[], [("edge_batch_fb",)], []]
    batches = list(reader.query_fluid_dynamics_history_batches(limit_seconds=100, batch_size=5))
    assert len(batches) == 1
    assert batches[0][0]["c1"] == "edge_batch_fb"

    # Batches without limit fallback
    mock_cursor.fetchmany.side_effect = [[], [("edge_batch_all_fb",)], []]
    batches_all = list(reader.query_fluid_dynamics_history_batches(limit_seconds=None, batch_size=5))
    assert len(batches_all) == 1

    # Exception handling
    mock_cursor.execute.side_effect = sqlite3.OperationalError("db error")
    assert reader.query_fluid_dynamics_history() == []
    assert reader.query_aggregated_fluid_dynamics() == []
    assert list(reader.query_fluid_dynamics_history_batches()) == []

