# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timedelta
import queue
import time
from unittest.mock import MagicMock
import pytest

from src.sas.traffic_data_recorder import TrafficDataRecorder


@pytest.fixture
def recorder_fixture():
    db = MagicMock()
    topo_mgr = MagicMock()
    topo_mgr.agent_maturity_cache = {"junc_1": "ADULT", "edge_2": "CHILD"}
    lm = MagicMock()
    lm.get_string.side_effect = lambda k, **kw: f"mock_{k}"

    topology = {
        "edge_1": {"to": "junc_1", "length": 100.0, "lanes": 2, "max_speed": 16.6},
        "edge_2": {"to": None, "length": 50.0, "lanes": 1, "max_speed": 11.1},
    }

    rec = TrafficDataRecorder(
        db_manager=db,
        topology_edges=topology,
        batch_size=1,
        locale_manager=lm,
        topology_manager=topo_mgr,
    )
    yield rec, db, topo_mgr, lm
    rec.close()


def test_traffic_data_recorder_init_and_properties(recorder_fixture):
    rec, db, _, _ = recorder_fixture
    assert rec.scenario_name == "default"
    assert rec.total_recorded == 0

    rec.set_scenario_name("scen_alpha")
    assert rec.scenario_name == "scen_alpha"

    new_topo = {"edge_3": {"length": 200.0}}
    rec.set_topology(new_topo)
    assert rec.topology == new_topo


def test_traffic_data_recorder_record_frame_and_flush(recorder_fixture):
    rec, db, _, _ = recorder_fixture

    mock_state_1 = MagicMock(mean_speed=10.0, density=0.2, queue_length=3, occupancy=0.15)
    mock_state_2 = MagicMock(mean_speed=15.0, density=0.1, queue_length=0, occupancy=0.05)
    frame = MagicMock()
    frame.edges = {
        "edge_1": mock_state_1,
        "edge_2": mock_state_2,
    }

    # Simulate old timestamp so 60s window triggers
    rec._last_ram_flush = datetime.now() - timedelta(seconds=70)

    rec.record_frame(frame)

    # Wait for background worker to process queue
    time.sleep(0.1)

    assert db.insert_synapse_fluid_dynamics.called
    samples = db.insert_synapse_fluid_dynamics.call_args[0][0]
    assert len(samples) == 2
    assert rec.total_recorded == 2

    sample_1 = next(s for s in samples if s["edge_id"] == "edge_1")
    assert sample_1["intersection_id"] == "junc_1"
    assert sample_1["maturity_stage"] == "ADULT"
    assert sample_1["mean_speed"] == 10.0
    assert sample_1["max_queue"] == 3


def test_traffic_data_recorder_queue_full(recorder_fixture):
    rec, _, _, _ = recorder_fixture

    # Fill batch buffer
    rec._batch_buffer = [{"dummy": 1}]
    # Mock _flush_queue.put_nowait to raise Full
    rec._flush_queue.put_nowait = MagicMock(side_effect=queue.Full())

    rec.flush()
    assert rec._batch_buffer == []
