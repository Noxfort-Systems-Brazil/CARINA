# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import time
from unittest.mock import MagicMock

import pytest

from communication.hft_diagnostics import HFTDiagnostics
from controller.traffic_frame_processor import TrafficFrameProcessor


@pytest.mark.benchmark
@pytest.mark.integration
def test_hft_frame_processing_sla_50_steps():
    ai_pipe_conn = MagicMock()
    watchdog_queue = MagicMock()
    sds_data_queue = MagicMock()
    failsafe_manager = MagicMock()
    topology_manager = MagicMock()
    telemetry_aggregator = MagicMock()
    override_manager = MagicMock()

    processor = TrafficFrameProcessor(
        ai_pipe_conn=ai_pipe_conn,
        watchdog_queue=watchdog_queue,
        sds_data_queue=sds_data_queue,
        failsafe_manager=failsafe_manager,
        topology_manager=topology_manager,
        telemetry_aggregator=telemetry_aggregator,
        override_manager=override_manager,
        traffic_data_recorder=None,
    )
    processor.set_system_ready(True)

    # Mock frame
    frame = MagicMock()
    frame.timestamp = 1000.0
    frame.agents = {"tl_1": MagicMock(), "tl_2": MagicMock()}
    frame.global_features = [0.1, 0.2, 0.3]

    latencies = []
    diagnostics = HFTDiagnostics()

    # Warm up 1 iteration
    processor.process_traffic_frame(frame)

    # Run 50 consecutive frames
    for i in range(50):
        frame.timestamp = 1000.0 + i
        t0 = time.perf_counter()
        delta_ms = processor.process_traffic_frame(frame)
        t_elapsed_ms = (time.perf_counter() - t0) * 1000.0

        effective_delta = delta_ms if delta_ms is not None else t_elapsed_ms
        latencies.append(effective_delta)

        # Log via diagnostics
        diagnostics.log_processing(
            recv_time=time.time(), proc_delta_ms=effective_delta, queue_depth=0, backpressure_threshold=10
        )

    import sys

    is_tracing = sys.gettrace() is not None
    threshold_ms = 200.0 if is_tracing else 100.0

    avg_ms = sum(latencies) / len(latencies)
    max_ms = max(latencies)

    # SLA requirement: each frame must process in < threshold
    assert max_ms < threshold_ms, f"Max processing latency {max_ms:.2f}ms exceeded {threshold_ms}ms SLA threshold"
    assert avg_ms < threshold_ms / 2, f"Average processing latency {avg_ms:.2f}ms too high"
    assert len(latencies) == 50
