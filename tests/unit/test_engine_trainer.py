# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from unittest.mock import MagicMock
import pytest

from engine.trainer import Trainer


def test_trainer_initialization():
    """Verifies that Trainer facade holds references and defaults correctly."""
    mock_loader = MagicMock()
    mock_router = MagicMock()
    mock_pipe = MagicMock()

    trainer = Trainer(scenario_loader=mock_loader, event_router=mock_router, pipe_conn=mock_pipe)
    assert trainer.is_running is True
    assert trainer.scenario_loader is mock_loader
    assert trainer.event_router is mock_router
    assert trainer.pipe_conn is mock_pipe


def test_trainer_properties_delegate_to_scenario_loader():
    """Verifies that properties on Trainer transparently delegate to ScenarioLoader."""
    mock_loader = MagicMock()
    mock_loader.agents = {"TL1": MagicMock()}
    mock_loader.strategist = "mock_strat"
    mock_loader.guardians = {"TL1": "mock_guardian"}
    mock_loader.current_map_path = "/path/to/net.xml"

    trainer = Trainer(scenario_loader=mock_loader, event_router=MagicMock(), pipe_conn=MagicMock())
    assert trainer.agents == mock_loader.agents
    assert trainer.strategist == "mock_strat"
    assert trainer.guardians == {"TL1": "mock_guardian"}
    assert trainer.current_map_path == "/path/to/net.xml"


def test_trainer_start_continuous_service():
    """Verifies that start_continuous_service signals backend_ready and starts event router."""
    mock_pipe = MagicMock()
    mock_router = MagicMock()
    trainer = Trainer(scenario_loader=MagicMock(), event_router=mock_router, pipe_conn=mock_pipe)

    trainer.start_continuous_service()

    mock_pipe.send.assert_called_once_with(("system", "backend_ready", (), {}))
    mock_router.start_continuous_service.assert_called_once()


def test_trainer_load_map_delegation():
    """Verifies that _load_map delegates cleanly to scenario_loader.load_scenario."""
    mock_loader = MagicMock()
    trainer = Trainer(scenario_loader=mock_loader, event_router=MagicMock(), pipe_conn=MagicMock())

    trainer._load_map("/maps/city.net.xml")
    mock_loader.load_scenario.assert_called_once_with("/maps/city.net.xml")


def test_trainer_connection_manager_and_supervisor_properties():
    """Verifies that Trainer exposes connection_manager, action_supervisor, and state_reconciler."""
    mock_cm = MagicMock()
    mock_as = MagicMock()
    mock_sr = MagicMock()

    trainer = Trainer(
        scenario_loader=MagicMock(),
        event_router=MagicMock(),
        pipe_conn=MagicMock(),
        connection_manager=mock_cm,
        action_supervisor=mock_as,
        state_reconciler=mock_sr,
    )

    assert trainer.connection_manager is mock_cm
    assert trainer.action_supervisor is mock_as
    assert trainer.state_reconciler is mock_sr


def test_event_router_toggle_connection_command():
    """Verifies EventRouter executes toggle_connection via trainer or step_processor without AttributeError."""
    from engine.event_router import EventRouter

    mock_cm = MagicMock()
    mock_cm.toggle_connection.return_value = True
    mock_as = MagicMock()
    mock_as.connection_manager = mock_cm

    mock_step_processor = MagicMock()
    mock_step_processor.action_supervisor = mock_as

    mock_trainer = Trainer(
        scenario_loader=MagicMock(),
        event_router=None,
        pipe_conn=MagicMock(),
        connection_manager=mock_cm,
        action_supervisor=mock_as,
    )

    router = EventRouter(
        pipe_conn=MagicMock(),
        trainer_instance=mock_trainer,
        agent_manager=MagicMock(),
        step_processor=mock_step_processor,
    )

    router._execute_command("hardware", "toggle_connection", ("TL_1", "192.168.1.100", "connect"))
    mock_cm.toggle_connection.assert_called_once_with("TL_1", "192.168.1.100", action="connect")
