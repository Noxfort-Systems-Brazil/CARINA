# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import math
from unittest.mock import MagicMock
import pytest

from controller.traffic_frame_processor import TrafficFrameProcessor


@pytest.fixture
def processor_fixture():
    ai_pipe_conn = MagicMock()
    watchdog_queue = MagicMock()
    sds_data_queue = MagicMock()
    failsafe_manager = MagicMock()
    failsafe_manager.failsafe_active = False
    topology_manager = MagicMock()
    telemetry_aggregator = MagicMock()
    telemetry_aggregator.should_update.return_value = False
    override_manager = MagicMock()
    override_manager.active_street_overrides = {}

    processor = TrafficFrameProcessor(
        ai_pipe_conn=ai_pipe_conn,
        watchdog_queue=watchdog_queue,
        sds_data_queue=sds_data_queue,
        failsafe_manager=failsafe_manager,
        topology_manager=topology_manager,
        telemetry_aggregator=telemetry_aggregator,
        override_manager=override_manager,
    )
    return processor, ai_pipe_conn, failsafe_manager, override_manager


def test_sanitize_metric_valid_within_bounds():
    val = TrafficFrameProcessor._sanitize_metric(0.75, 0.0, 1.0, default=0.0)
    assert val == 0.75

    speed = TrafficFrameProcessor._sanitize_metric(13.89, 0.0, 100.0, default=0.0)
    assert speed == 13.89


def test_sanitize_metric_nan_inf_and_invalids():
    # NaN check
    assert TrafficFrameProcessor._sanitize_metric(float("nan"), 0.0, 1.0, default=0.0) == 0.0

    # Inf checks
    assert TrafficFrameProcessor._sanitize_metric(float("inf"), 0.0, 100.0, default=0.0) == 0.0
    assert TrafficFrameProcessor._sanitize_metric(float("-inf"), 0.0, 100.0, default=0.0) == 0.0

    # None and invalid types
    assert TrafficFrameProcessor._sanitize_metric(None, 0.0, 10.0, default=0.0) == 0.0
    assert TrafficFrameProcessor._sanitize_metric("not_a_number", 0.0, 10.0, default=0.0) == 0.0


def test_sanitize_metric_boundary_clamping():
    # Occupancy clamping [0.0, 1.0]
    assert TrafficFrameProcessor._sanitize_metric(-0.25, 0.0, 1.0) == 0.0
    assert TrafficFrameProcessor._sanitize_metric(1.5, 0.0, 1.0) == 1.0

    # Speed clamping [0.0, 100.0]
    assert TrafficFrameProcessor._sanitize_metric(-1.0, 0.0, 100.0) == 0.0
    assert TrafficFrameProcessor._sanitize_metric(250.0, 0.0, 100.0) == 100.0

    # Queue clamping [0.0, 1000.0]
    assert TrafficFrameProcessor._sanitize_metric(-5.0, 0.0, 1000.0) == 0.0
    assert TrafficFrameProcessor._sanitize_metric(5000.0, 0.0, 1000.0) == 1000.0


def test_sanitize_edge_state_with_object_and_dict(processor_fixture):
    processor, _, _, _ = processor_fixture

    # Test with object (Protobuf / Mock)
    state_obj = MagicMock()
    state_obj.occupancy = 0.45
    state_obj.mean_speed = 12.5
    state_obj.queue_length = 3
    state_obj.density = 0.2

    clean_obj = processor._sanitize_edge_state("edge_1", state_obj)
    assert clean_obj["occupancy"] == 0.45
    assert clean_obj["mean_speed"] == 12.5
    assert clean_obj["queue_length"] == 3.0
    assert clean_obj["density"] == 0.2

    # Test with dict
    state_dict = {
        "occupancy": 0.85,
        "mean_speed": 8.0,
        "queue_length": 10,
        "density": 0.5,
    }
    clean_dict = processor._sanitize_edge_state("edge_2", state_dict)
    assert clean_dict["occupancy"] == 0.85
    assert clean_dict["mean_speed"] == 8.0
    assert clean_dict["queue_length"] == 10.0
    assert clean_dict["density"] == 0.5


def test_process_traffic_frame_nan_and_inf_injection(processor_fixture):
    processor, ai_pipe_conn, _, _ = processor_fixture

    frame = MagicMock()
    frame.timestamp = 100.0
    frame.sequence_id = 42

    edge_nan = MagicMock()
    edge_nan.occupancy = float("nan")
    edge_nan.mean_speed = float("nan")
    edge_nan.queue_length = float("nan")
    edge_nan.density = float("nan")

    edge_inf = MagicMock()
    edge_inf.occupancy = float("inf")
    edge_inf.mean_speed = float("-inf")
    edge_inf.queue_length = float("inf")
    edge_inf.density = float("inf")

    frame.edges = {
        "edge_nan": edge_nan,
        "edge_inf": edge_inf,
    }

    processor.process_traffic_frame(frame)

    assert ai_pipe_conn.send.called
    sent_args = ai_pipe_conn.send.call_args[0][0]
    assert sent_args[0] == "custom"
    assert sent_args[1] == "hft_step"

    traffic_data = sent_args[2][0]
    assert traffic_data["timestamp"] == 100.0
    assert traffic_data["sequence_id"] == 42

    # Verify edge_nan sanitized to 0.0
    edges = traffic_data["edges"]
    assert edges["edge_nan"]["occupancy"] == 0.0
    assert edges["edge_nan"]["mean_speed"] == 0.0
    assert edges["edge_nan"]["queue_length"] == 0.0
    assert edges["edge_nan"]["density"] == 0.0
    assert not math.isnan(edges["edge_nan"]["occupancy"])

    # Verify edge_inf sanitized to 0.0
    assert edges["edge_inf"]["occupancy"] == 0.0
    assert edges["edge_inf"]["mean_speed"] == 0.0
    assert edges["edge_inf"]["queue_length"] == 0.0
    assert edges["edge_inf"]["density"] == 0.0
    assert not math.isinf(edges["edge_inf"]["mean_speed"])


def test_process_traffic_frame_boundary_clamping(processor_fixture):
    processor, ai_pipe_conn, _, _ = processor_fixture

    frame = MagicMock()
    frame.timestamp = 200.0
    frame.sequence_id = 43

    # Negative values (SUMO empty edge artifact -1.0 speed, negative occupancy/queue)
    edge_neg = MagicMock()
    edge_neg.occupancy = -0.7
    edge_neg.mean_speed = -1.0
    edge_neg.queue_length = -5
    edge_neg.density = -0.2

    # Extreme high out-of-boundary values
    edge_high = MagicMock()
    edge_high.occupancy = 1.8
    edge_high.mean_speed = 350.0
    edge_high.queue_length = 9999
    edge_high.density = 2.5

    frame.edges = {
        "edge_neg": edge_neg,
        "edge_high": edge_high,
    }

    processor.process_traffic_frame(frame)

    traffic_data = ai_pipe_conn.send.call_args[0][0][2][0]
    edges = traffic_data["edges"]

    # Negative clamped to 0.0
    assert edges["edge_neg"]["occupancy"] == 0.0
    assert edges["edge_neg"]["mean_speed"] == 0.0
    assert edges["edge_neg"]["queue_length"] == 0.0
    assert edges["edge_neg"]["density"] == 0.0

    # High clamped to upper limits
    assert edges["edge_high"]["occupancy"] == 1.0
    assert edges["edge_high"]["mean_speed"] == 100.0
    assert edges["edge_high"]["queue_length"] == 1000.0
    assert edges["edge_high"]["density"] == 1.0


def test_process_traffic_frame_timestamp_sanitization(processor_fixture):
    processor, ai_pipe_conn, _, _ = processor_fixture

    # Test NaN timestamp
    frame_nan = MagicMock()
    frame_nan.timestamp = float("nan")
    frame_nan.sequence_id = 1
    frame_nan.edges = {}

    processor.process_traffic_frame(frame_nan)
    traffic_data_nan = ai_pipe_conn.send.call_args[0][0][2][0]
    assert traffic_data_nan["timestamp"] == 0.0
    assert not math.isnan(traffic_data_nan["timestamp"])

    # Test Inf timestamp
    frame_inf = MagicMock()
    frame_inf.timestamp = float("inf")
    frame_inf.sequence_id = 2
    frame_inf.edges = {}

    processor.process_traffic_frame(frame_inf)
    traffic_data_inf = ai_pipe_conn.send.call_args[0][0][2][0]
    assert traffic_data_inf["timestamp"] == 0.0
    assert not math.isinf(traffic_data_inf["timestamp"])

    # Test negative timestamp
    frame_neg = MagicMock()
    frame_neg.timestamp = -123.4
    frame_neg.sequence_id = 3
    frame_neg.edges = {}

    processor.process_traffic_frame(frame_neg)
    traffic_data_neg = ai_pipe_conn.send.call_args[0][0][2][0]
    assert traffic_data_neg["timestamp"] == 0.0


def test_process_traffic_frame_blocked_street_override(processor_fixture):
    processor, ai_pipe_conn, _, override_manager = processor_fixture

    override_manager.active_street_overrides = {"edge_blocked": "BLOCKED"}

    frame = MagicMock()
    frame.timestamp = 300.0
    frame.sequence_id = 50

    blocked_edge = MagicMock()
    blocked_edge.occupancy = float("nan")
    blocked_edge.mean_speed = 80.0
    blocked_edge.queue_length = 50

    frame.edges = {"edge_blocked": blocked_edge}

    processor.process_traffic_frame(frame)

    traffic_data = ai_pipe_conn.send.call_args[0][0][2][0]
    edge_res = traffic_data["edges"]["edge_blocked"]
    assert edge_res["occupancy"] == 0.0
    assert edge_res["mean_speed"] == 0.0
    assert edge_res["queue_length"] == 0.0


def test_process_traffic_frame_failsafe_blocks_ai_send(processor_fixture):
    processor, ai_pipe_conn, failsafe_manager, _ = processor_fixture
    failsafe_manager.failsafe_active = True

    frame = MagicMock()
    frame.timestamp = 400.0
    frame.sequence_id = 60
    frame.edges = {}

    processor.process_traffic_frame(frame)
    assert not ai_pipe_conn.send.called
