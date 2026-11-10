# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from unittest.mock import MagicMock
import pytest

from engine.step_telemetry_publisher import StepTelemetryPublisher


def test_publisher_without_pipe():
    """Verifies that publish returns False safely when pipe_conn is None."""
    pub = StepTelemetryPublisher(pipe_conn=None)
    success = pub.publish(
        sim_time=10.0,
        edges_data={},
        current_stages={},
        tls_lanes_state={},
        maturity_info={},
    )
    assert success is False


def test_publisher_successful_dispatch():
    """Verifies that publish builds the expected payload and sends it through pipe_conn."""
    mock_pipe = MagicMock()
    pub = StepTelemetryPublisher(pipe_conn=mock_pipe)

    success = pub.publish(
        sim_time=12.5,
        edges_data={"edge1": {"occupancy": 0.3}},
        current_stages={"TL1": 2},
        tls_lanes_state={"TL1": {}},
        maturity_info={"TL1": "AUTONOMOUS"},
        mfd_data={"efficiency": 0.88},
    )

    assert success is True
    mock_pipe.send.assert_called_once()
    msg_type, payload = mock_pipe.send.call_args[0][0]
    assert msg_type == "ai_telemetry_sync"
    assert payload["sim_time"] == 12.5
    assert payload["edges"] == {"edge1": {"occupancy": 0.3}}
    assert payload["tls_phases"] == {"TL1": 2}
    assert payload["maturity"] == {"TL1": "AUTONOMOUS"}
    assert payload["mfd"] == {"efficiency": 0.88}


def test_publisher_exception_handling():
    """Verifies that publisher catches transport exceptions without crashing."""
    mock_pipe = MagicMock()
    mock_pipe.send.side_effect = BrokenPipeError("Pipe disconnected")

    pub = StepTelemetryPublisher(pipe_conn=mock_pipe)
    success = pub.publish(
        sim_time=1.0,
        edges_data={},
        current_stages={},
        tls_lanes_state={},
        maturity_info={},
    )
    assert success is False


def test_publisher_set_pipe_conn():
    """Verifies updating connection handle."""
    pub = StepTelemetryPublisher(pipe_conn=None)
    mock_pipe = MagicMock()
    pub.set_pipe_conn(mock_pipe)
    assert pub.pipe_conn is mock_pipe
