# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from unittest.mock import MagicMock, patch
import pytest
import torch

from engine.online_pae_trainer import OnlinePAETrainer


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.getint.return_value = 5
    settings.getfloat.return_value = 5e-4
    return settings


@pytest.fixture
def mock_agent_manager():
    mgr = MagicMock()
    mgr.shared_pae = MagicMock()
    mgr.shared_pae.history_len = 8
    mgr.shared_pae.input_dim = 40
    mgr.shared_pae.pad_to_input_dim.side_effect = lambda t: t
    return mgr


def test_online_pae_trainer_initialization(mock_settings, mock_agent_manager):
    """Verifies default initialization and frequency configuration."""
    trainer = OnlinePAETrainer(settings=mock_settings, agent_manager=mock_agent_manager)
    assert trainer.pae_update_frequency == 5
    assert trainer._last_pae_update_time == -5
    assert trainer.pae_memory is None


def test_online_pae_trainer_frequency_throttling(mock_settings, mock_agent_manager):
    """Verifies that train_step does not execute before frequency interval."""
    mock_opt = MagicMock()
    trainer = OnlinePAETrainer(settings=mock_settings, agent_manager=mock_agent_manager, pae_optimizer=mock_opt)

    agents = {"TL1": MagicMock()}
    trainer.train_step(sim_time=2.0, agents=agents)
    mock_opt.step.assert_not_called()
    mock_opt.step_from_memory.assert_not_called()


def test_online_pae_trainer_execution_with_shared_pae(mock_settings, mock_agent_manager):
    """Verifies that train_step samples transitions and invokes optimizer."""
    mock_opt = MagicMock()
    mock_opt.device = torch.device("cpu")
    mock_opt.step.return_value = 0.042

    trainer = OnlinePAETrainer(settings=mock_settings, agent_manager=mock_agent_manager, pae_optimizer=mock_opt)

    # Setup agent with state memory
    agent = MagicMock()
    agent.memory = MagicMock()
    agent.memory.states = [
        [[0.1] * 40] * 8,  # S_{t-1}
        [[0.2] * 40] * 8,  # S_t
    ]
    agent.memory.__len__.return_value = 2

    # Disable memory buffer push to trigger direct batch step
    with patch("engine.online_pae_trainer.OnlinePAETrainer._execute_online_training") as mock_exec:
        trainer.train_step(sim_time=5.0, agents={"TL1": agent})
        mock_exec.assert_called_once_with({"TL1": agent})
        assert trainer._last_pae_update_time == 5.0


def test_online_pae_trainer_reset(mock_settings, mock_agent_manager):
    """Verifies that reset restores initial timing state."""
    trainer = OnlinePAETrainer(settings=mock_settings, agent_manager=mock_agent_manager)
    trainer._last_pae_update_time = 100.0
    trainer.reset()
    assert trainer._last_pae_update_time == -5
