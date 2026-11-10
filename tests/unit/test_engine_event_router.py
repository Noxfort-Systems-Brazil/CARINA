# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from unittest.mock import MagicMock, patch
import pytest

from src.engine.event_router import EventRouter


@pytest.fixture
def router_fixture():
    pipe_conn = MagicMock()
    trainer = MagicMock()
    trainer.is_running = True
    trainer.agents = {"TL_1": MagicMock()}
    trainer.current_map_path = "map.net.xml"
    trainer.strategist = MagicMock()

    agent_mgr = MagicMock()
    step_proc = MagicMock()

    router = EventRouter(
        pipe_conn=pipe_conn,
        trainer_instance=trainer,
        agent_manager=agent_mgr,
        step_processor=step_proc,
    )
    return router, pipe_conn, trainer, agent_mgr, step_proc


def test_event_router_execute_command_hft_step(router_fixture):
    router, _, trainer, _, step_proc = router_fixture

    # 1. With agents
    router._execute_command("custom", "hft_step", ({"data": 123},))
    step_proc.process_hft_step.assert_called_once_with({"data": 123}, trainer.agents)
    assert router._ai_started_logged is True

    # 2. Without agents (warning logged)
    trainer.agents = {}
    with patch("time.time", return_value=100.0):
        router._execute_command("custom", "hft_step", ({"data": 123},))
        assert router._last_warn_time == 100.0



def test_event_router_execute_command_load_map_and_checkpoint(router_fixture):
    router, _, trainer, agent_mgr, _ = router_fixture

    router._execute_command("custom", "load_map", ("new_map.xml",))
    trainer._load_map.assert_called_once_with("new_map.xml")

    router._execute_command("system", "save_checkpoint", ())
    agent_mgr.save_system_state.assert_called_once_with(
        trainer.current_map_path, trainer.agents, trainer.strategist
    )


def test_event_router_execute_command_hardware_toggle(router_fixture):
    router, _, trainer, _, step_proc = router_fixture

    # Hardware connection manager on trainer
    mock_conn_mgr = MagicMock()
    mock_conn_mgr.toggle_connection.return_value = False  # disconnected
    trainer.connection_manager = mock_conn_mgr
    mock_supervisor = MagicMock()
    trainer.action_supervisor = mock_supervisor

    router._execute_command("hardware", "toggle_connection", ("TL_1", "127.0.0.1:502", "disconnect"))
    mock_conn_mgr.toggle_connection.assert_called_once_with("TL_1", "127.0.0.1:502", action="disconnect")
    mock_supervisor.cleanup_intersection.assert_called_once_with("TL_1")

    # When no conn_mgr exists
    trainer.connection_manager = None
    step_proc.action_supervisor = None
    router._execute_command("hardware", "toggle_connection", ("TL_1", "127.0.0.1:502"))


def test_event_router_execute_command_hardware_override_and_fenix_and_shutdown(router_fixture):
    router, _, trainer, _, step_proc = router_fixture

    # Apply override with supervisor
    mock_sup = MagicMock()
    step_proc.action_supervisor = mock_sup
    trainer.action_supervisor = None
    router._execute_command("hardware", "apply_override", ("TL_1", "EMERGENCY"))
    mock_sup.apply_hardware_override.assert_called_once_with("TL_1", "EMERGENCY")

    # Apply override without supervisor
    step_proc.action_supervisor = None
    router._execute_command("hardware", "apply_override", ("TL_1", "NORMAL"))

    # Fenix reconcile stages
    mock_reconciler = MagicMock()
    trainer.state_reconciler = mock_reconciler
    router._execute_command("fenix", "reconcile_stages", ({"TL_1": 2},))
    mock_reconciler.reconcile_with_field.assert_called_once_with({"TL_1": 2})

    # System shutdown
    router._execute_command("system", "shutdown", ())
    assert trainer.is_running is False


def test_event_router_start_continuous_service_loop(router_fixture):
    router, pipe_conn, trainer, _, step_proc = router_fixture

    # Simulate 1 loop with 3 conflated commands: malformed, hft_step 1, hft_step 2 (dropped frame), then EOF
    pipe_conn.poll.side_effect = [True, True, True, False, False]
    pipe_conn.recv.side_effect = [
        "invalid_cmd",
        ["custom", "hft_step", ({"frame": 1},)],
        ["custom", "hft_step", ({"frame": 2},)],
    ]

    # After first iteration, trainer.is_running set to False to exit loop
    def stop_trainer(*args, **kwargs):
        trainer.is_running = False

    step_proc.process_hft_step.side_effect = stop_trainer

    router.start_continuous_service()
    assert step_proc.process_hft_step.called


def test_event_router_start_continuous_service_eof(router_fixture):
    router, pipe_conn, trainer, _, _ = router_fixture

    pipe_conn.poll.return_value = True
    pipe_conn.recv.side_effect = EOFError()

    router.start_continuous_service()
    assert trainer.is_running is False


def test_event_router_start_continuous_service_drain_eof(router_fixture):
    router, pipe_conn, trainer, _, _ = router_fixture

    pipe_conn.poll.side_effect = [True, True]
    pipe_conn.recv.side_effect = [
        ["system", "shutdown", ()],
        EOFError(),
    ]

    router.start_continuous_service()
    assert trainer.is_running is False


def test_event_router_start_continuous_service_keyboard_interrupt(router_fixture):
    router, pipe_conn, trainer, _, _ = router_fixture

    pipe_conn.poll.side_effect = KeyboardInterrupt()

    router.start_continuous_service()
    assert trainer.is_running is False


def test_event_router_start_continuous_service_general_error_recovered(router_fixture):
    router, pipe_conn, trainer, _, _ = router_fixture

    # First iteration raises RuntimeError, second iteration trainer stops
    def set_false(*args, **kwargs):
        trainer.is_running = False
        raise RuntimeError("Pipe error")

    pipe_conn.poll.side_effect = set_false

    router.start_continuous_service()
    assert trainer.is_running is False
