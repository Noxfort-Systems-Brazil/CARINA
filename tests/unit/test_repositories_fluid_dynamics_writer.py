# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
import sqlite3
from unittest.mock import MagicMock
import pytest

from src.repositories.fluid_dynamics_writer import FluidDynamicsWriter


@pytest.fixture
def writer_fixture():
    engine = MagicMock()
    qp = MagicMock()
    writer = FluidDynamicsWriter(engine, qp)
    return writer, engine, qp


def test_fluid_dynamics_writer_edge_id_cache_and_db(writer_fixture):
    writer, _, _ = writer_fixture

    # 1. Cache hit
    writer._edge_dict_cache["edge_cached"] = 42
    assert writer._get_or_create_edge_id(None, "edge_cached") == 42

    # 2. DB select hit
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = (101,)
    mock_conn.cursor.return_value = mock_cursor

    val = writer._get_or_create_edge_id(mock_conn, "edge_db")
    assert val == 101
    assert writer._edge_dict_cache["edge_db"] == 101

    # 3. DB insert when not found initially
    mock_cursor.fetchone.side_effect = [None, (202,)]
    val_insert = writer._get_or_create_edge_id(mock_conn, "edge_new")
    assert val_insert == 202
    assert mock_conn.commit.called

    # 4. Error handled
    mock_cursor.execute.side_effect = sqlite3.OperationalError("Table missing")
    assert writer._get_or_create_edge_id(mock_conn, "edge_err") == 0


def test_fluid_dynamics_writer_delta_compression(writer_fixture):
    writer, _, _ = writer_fixture

    sample1 = {"edge_id": "e1", "density": 0.5, "mean_speed": 10.0, "queue_length": 2, "occupancy": 0.2}
    sample2_identical = {"edge_id": "e1", "density": 0.5, "mean_speed": 10.0, "queue_length": 2, "occupancy": 0.2}
    sample3_diff = {"edge_id": "e1", "density": 0.8, "mean_speed": 5.0, "queue_length": 5, "occupancy": 0.4}

    # First and second identical: nothing compressed yet (sample2 continues sample1)
    compressed_1 = writer._apply_delta_compression([sample1, sample2_identical])
    assert len(compressed_1) == 0
    assert writer._last_edge_samples["e1"][0]["sample_count"] == 2

    # Third different: emits sample1 (with sample_count 2)
    compressed_2 = writer._apply_delta_compression([sample3_diff])
    assert len(compressed_2) == 1
    assert compressed_2[0]["sample_count"] == 2


def test_fluid_dynamics_writer_insert_synapse_fluid_dynamics(writer_fixture):
    writer, engine, _ = writer_fixture

    # Empty samples
    writer.insert_synapse_fluid_dynamics([])
    assert not engine.get_connection.called

    # Conn None
    engine.get_connection.return_value = None
    writer.insert_synapse_fluid_dynamics([{"edge_id": "e1"}])

    # Normal insertion
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    engine.get_connection.return_value = mock_conn

    # 2 different samples so at least 1 is compressed and emitted
    samples = [
        {"edge_id": "e1", "density": 0.1, "mean_speed": 15.0, "queue_length": 0, "occupancy": 0.05},
        {"edge_id": "e1", "density": 0.9, "mean_speed": 2.0, "queue_length": 10, "occupancy": 0.8},
    ]

    writer._edge_dict_cache["e1"] = 10
    writer.insert_synapse_fluid_dynamics(samples)

    assert mock_cursor.executemany.called
    assert mock_conn.commit.called
    assert mock_conn.close.called


def test_fluid_dynamics_writer_insert_error_rollback(writer_fixture):
    writer, engine, _ = writer_fixture

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.executemany.side_effect = sqlite3.OperationalError("Disk error")
    mock_conn.cursor.return_value = mock_cursor
    engine.get_connection.return_value = mock_conn

    samples = [
        {"edge_id": "e2", "density": 0.1, "mean_speed": 15.0, "queue_length": 0, "occupancy": 0.05},
        {"edge_id": "e2", "density": 0.9, "mean_speed": 2.0, "queue_length": 10, "occupancy": 0.8},
    ]

    writer.insert_synapse_fluid_dynamics(samples)

    assert mock_conn.rollback.called
    assert mock_conn.close.called
