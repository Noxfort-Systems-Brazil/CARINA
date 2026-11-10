# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from queue import Full
from unittest.mock import MagicMock
import pytest

from src.handlers.ai_request_handler import AIRequestHandler


@pytest.fixture
def handler_fixture():
    lm = MagicMock()
    lm.get_string.side_effect = lambda k, **kw: f"mock_{k}"

    topo_mgr = MagicMock()
    topo_mgr.agent_maturity_cache = {}
    del topo_mgr.tls_phases_cache  # ensure missing initially

    sds_queue = MagicMock()
    sas_queue = MagicMock()
    health_mon = MagicMock()
    override_mgr = MagicMock()
    override_mgr.is_ai_command_blocked.return_value = False
    override_mgr.active_overrides = {"tl_1": "EMERGENCY"}

    handler = AIRequestHandler(
        locale_manager=lm,
        topology_manager=topo_mgr,
        sds_queue=sds_queue,
        sas_queue=sas_queue,
        health_monitor=health_mon,
        override_manager=override_mgr,
    )
    return handler, topo_mgr, sds_queue, sas_queue, health_mon, override_mgr


def test_ai_telemetry_sync(handler_fixture):
    handler, topo_mgr, sds_queue, sas_queue, health_mon, _ = handler_fixture

    payload = {
        "maturity": {"tl_1": "ADULT"},
        "tls_phases": {"tl_1": 2},
        "edges": {"edge_1": 10},
    }
    request = ("ai_telemetry_sync", payload)

    handler.process(request, sumo_conn=MagicMock(), ai_pipe_conn=MagicMock(), override_commands_buffer=[])

    assert topo_mgr.agent_maturity_cache["tl_1"] == "ADULT"
    assert topo_mgr.tls_phases_cache["tl_1"] == 2
    assert sas_queue.put_nowait.called
    assert sds_queue.put_nowait.called
    # Telemetry should not trigger health_mon.record_activity
    assert not health_mon.record_activity.called


def test_ai_telemetry_sync_queue_full(handler_fixture):
    handler, _, sds_queue, sas_queue, _, _ = handler_fixture

    sas_queue.put_nowait.side_effect = Full()
    payload = {"maturity": {"tl_1": "CHILD"}}
    request = ("ai_telemetry_sync", payload)

    # Should not raise
    handler.process(request, sumo_conn=MagicMock(), ai_pipe_conn=MagicMock(), override_commands_buffer=[])


def test_backend_ready_callback(handler_fixture):
    handler, _, _, _, _, _ = handler_fixture

    cb = MagicMock()
    handler.set_backend_ready_callback(cb)

    request = ("system", "backend_ready")
    handler.process(request, sumo_conn=MagicMock(), ai_pipe_conn=MagicMock(), override_commands_buffer=[])

    cb.assert_called_once()


def test_process_command_blocked_by_override(handler_fixture):
    handler, _, _, _, health_mon, override_mgr = handler_fixture
    override_mgr.is_ai_command_blocked.return_value = True

    pipe = MagicMock()
    request = ("trafficlight", "setPhase", ("tl_1", 2), {})

    handler.process(request, sumo_conn=MagicMock(), ai_pipe_conn=pipe, override_commands_buffer=[])

    health_mon.record_activity.assert_called_once()
    pipe.send.assert_called_once_with(None)


def test_custom_update_maturity_state(handler_fixture):
    handler, topo_mgr, _, _, _, _ = handler_fixture

    pipe = MagicMock()
    data = {
        "tl_1": "ADULT",
        "tl_2": "CHILD",
        "run_id": 42,
    }
    request = ("custom", "update_maturity_state", (data,), {})

    handler.process(request, sumo_conn=MagicMock(), ai_pipe_conn=pipe, override_commands_buffer=[])

    assert handler.current_run_id == 42
    assert topo_mgr.agent_maturity_cache["tl_1"] == "ADULT"
    pipe.send.assert_called_once_with(True)


def test_custom_update_maturity_state_with_explicit_agent_maturity(handler_fixture):
    handler, topo_mgr, _, _, _, _ = handler_fixture

    pipe = MagicMock()
    data = {
        "agent_maturity": {"tl_3": "ADULT"},
    }
    request = ("custom", "update_maturity_state", (data,), {})

    handler.process(request, sumo_conn=MagicMock(), ai_pipe_conn=pipe, override_commands_buffer=[])
    assert topo_mgr.agent_maturity_cache["tl_3"] == "ADULT"
    pipe.send.assert_called_once_with(True)


def test_custom_get_batched_step_data_not_callable(handler_fixture):
    handler, _, _, _, _, _ = handler_fixture

    pipe = MagicMock()
    request = ("custom", "get_batched_step_data", (), {})

    # collect_step_data_func is None
    handler.process(request, sumo_conn=MagicMock(), ai_pipe_conn=pipe, override_commands_buffer=[], collect_step_data_func=None)
    assert not pipe.send.called


def test_custom_get_batched_step_data_success_with_buffer(handler_fixture):
    handler, _, sds_queue, sas_queue, _, _ = handler_fixture

    pipe = MagicMock()
    request = ("custom", "get_batched_step_data", (), {})

    mock_step_func = MagicMock(return_value={"step": 1})
    buffer = ["cmd1", "cmd2"]

    handler.process(
        request,
        sumo_conn=MagicMock(),
        ai_pipe_conn=pipe,
        override_commands_buffer=buffer,
        collect_step_data_func=mock_step_func,
    )

    assert buffer == []  # Buffer was cleared
    assert sds_queue.put_nowait.called
    assert sas_queue.put_nowait.called
    pipe.send.assert_called_once()
    sent_data = pipe.send.call_args[0][0]
    assert sent_data["override_commands"] == ["cmd1", "cmd2"]


def test_unknown_module_or_function(handler_fixture):
    handler, _, _, _, _, _ = handler_fixture

    pipe = MagicMock()
    request = ("unknown_mod", "unknown_func", (), {})

    # With sumo_conn
    handler.process(request, sumo_conn=MagicMock(), ai_pipe_conn=pipe, override_commands_buffer=[])
    sent_err = pipe.send.call_args[0][0]
    assert isinstance(sent_err, AttributeError)

    # Without sumo_conn
    pipe.reset_mock()
    handler.process(request, sumo_conn=None, ai_pipe_conn=pipe, override_commands_buffer=[])
    pipe.send.assert_called_once_with(None)
