# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import tempfile
import threading
import time
from unittest.mock import MagicMock

import pytest

from src.database.database_manager import DatabaseManager
from src.database.db_engine import DatabaseEngine
from src.repositories.step_decision_repo import StepDecisionRepository
from src.repositories.topology_dictionary_repo import TopologyDictionaryRepository
from src.sas.traffic_data_recorder import TrafficDataRecorder
from src.utils.local_agent_helpers import AgentCheckpointManager


@pytest.fixture
def temp_sqlite_engine():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        temp_path = f.name

    lm = MagicMock()
    engine = DatabaseEngine(locale_manager=lm, db_name=temp_path)
    engine.db_type = "sqlite"
    engine.db_path = temp_path

    yield engine

    try:
        os.remove(temp_path)
    except OSError:
        pass


def test_step_decision_repo_sqlite_upsert(temp_sqlite_engine):
    """Verifies that increment_decision_counter_batch performs atomic UPSERT in SQLite without errors."""
    lm = MagicMock()
    repo = StepDecisionRepository(temp_sqlite_engine, lm)
    assert repo.ensure_tables_exist() is True

    # Initial batch insert
    batch_1 = [(1001, 0, 5), (1001, 1, 2), (1002, 0, 10)]
    success_1 = repo.increment_decision_counter_batch(batch_1)
    assert success_1 is True

    # Upsert increment on existing keys
    batch_2 = [(1001, 0, 3), (1001, 1, 1)]
    success_2 = repo.increment_decision_counter_batch(batch_2)
    assert success_2 is True

    # Verify counts in SQLite
    conn = temp_sqlite_engine.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT agent_id, decision_code, count FROM step_decision_counters ORDER BY agent_id, decision_code")
    rows = cursor.fetchall()

    assert rows[0] == (1001, 0, 8)  # 5 + 3
    assert rows[1] == (1001, 1, 3)  # 2 + 1
    assert rows[2] == (1002, 0, 10)
    conn.close()


def test_topology_dictionary_repo_sqlite_bulk_save(temp_sqlite_engine):
    """Verifies that bulk_save_topology_elements works on SQLite without psycopg2 execute_values error."""
    repo = TopologyDictionaryRepository(temp_sqlite_engine)
    assert repo.ensure_table_exists() is True

    elements = [
        {
            "element_type": "junction",
            "raw_net_id": "j_1",
            "numeric_id": 1,
            "custom_name": "Cruzamento Central",
            "from_node": "n_1",
            "to_node": "n_2",
            "is_bidirectional_pair": False,
        },
        {
            "element_type": "junction",
            "raw_net_id": "j_2",
            "numeric_id": 2,
            "custom_name": "Avenida Sul",
            "from_node": "n_3",
            "to_node": "n_4",
            "is_bidirectional_pair": True,
        },
    ]

    success = repo.bulk_save_topology_elements(elements)
    assert success is True

    # Verify update on conflict
    elements[0]["custom_name"] = "Cruzamento Central Atualizado"
    success_update = repo.bulk_save_topology_elements(elements)
    assert success_update is True

    conn = temp_sqlite_engine.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT raw_net_id, custom_name FROM topology_dictionary WHERE raw_net_id = 'j_1'")
    row = cursor.fetchone()
    assert row[0] == "j_1"
    assert row[1] == "Cruzamento Central Atualizado"
    conn.close()


def test_database_manager_get_instance_prevents_thread_explosion():
    """Verifies that DatabaseManager.get_instance reuses the instance and does not create duplicate threads."""
    lm = MagicMock()
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        # Reset singleton for clean test
        DatabaseManager._instance = None

        initial_thread_count = threading.active_count()
        dm1 = DatabaseManager.get_instance(locale_manager=lm, db_name=db_path)
        threads_after_dm1 = threading.active_count()

        # Call get_instance 50 times (simulating frequent checkpoint saves)
        for _ in range(50):
            dm = DatabaseManager.get_instance(locale_manager=lm, db_name=db_path)
            assert dm is dm1

        # Thread count must NOT increase by 50!
        threads_after_50_calls = threading.active_count()
        assert threads_after_50_calls == threads_after_dm1

        dm1.close()
    finally:
        DatabaseManager._instance = None
        if os.path.exists(db_path):
            os.remove(db_path)


def test_traffic_data_recorder_worker_loop():
    """Verifies that TrafficDataRecorder._db_worker_loop runs and processes flushes without AttributeError."""
    mock_db = MagicMock()
    mock_db.insert_synapse_fluid_dynamics = MagicMock()

    recorder = TrafficDataRecorder(db_manager=mock_db, batch_size=2)
    assert recorder._worker_thread.is_alive()

    # Put sample into flush queue directly
    samples = [{"edge_id": "edge_1", "density": 0.5}]
    recorder._flush_queue.put(samples)

    # Wait for background thread to process
    time.sleep(0.2)

    assert mock_db.insert_synapse_fluid_dynamics.called
    assert recorder.total_recorded == 1

    recorder.close()
