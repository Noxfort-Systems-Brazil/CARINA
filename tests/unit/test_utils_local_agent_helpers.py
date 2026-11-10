# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
from unittest.mock import MagicMock, patch
import pytest
import torch
import torch.nn as nn

from src.utils.local_agent_helpers import (
    AgentCheckpointManager,
    AgentHyperparameterManager,
    PAEStateAugmentor,
)


def test_pae_state_augmentor():
    # 1. No PAE and no precomputed
    augmentor = PAEStateAugmentor(None)
    t = torch.zeros((2, 4, 8))
    assert augmentor.augment(t) is t

    # 2. With precomputed 1D latent
    t = torch.zeros((1, 4, 8))
    latent_1d = torch.ones((16,))
    res = augmentor.augment(t, precomputed_latent=latent_1d)
    assert res.shape == (1, 4, 8 + 16)

    # 3. With shared_pae
    mock_pae = MagicMock()
    mock_pae.latent_dim = 8
    mock_pae.encode.return_value = torch.ones((1, 8))
    augmentor_pae = PAEStateAugmentor(mock_pae)
    res_pae = augmentor_pae.augment(t)
    assert res_pae.shape == (1, 4, 8 + 8)


def test_agent_hyperparameter_manager():
    agent = MagicMock()
    agent.hyperparams = {
        "gamma": 0.95,
        "gae_lambda": 0.9,
        "learning_rate": 0.0005,
        "eps_clip": 0.15,
        "k_epochs": 8,
        "target_kl": 0.01,
        "grad_clip_norm": 1.0,
        "dropout_p": 0.2,
    }
    agent.optimizer = MagicMock()
    agent.optimizer.param_groups = [{}]

    class CustomDropout:
        p = 0.1

    custom_dropout = CustomDropout()
    mock_net = MagicMock()
    mock_net.modules.return_value = [custom_dropout]
    agent.policy_net = mock_net

    with patch.object(nn, "Dropout", CustomDropout):
        AgentHyperparameterManager.update(agent, agent.hyperparams)

    assert agent.gamma == 0.95
    assert agent.k_epochs == 8
    assert agent.optimizer.param_groups[0]["lr"] == 0.0005
    assert custom_dropout.p == 0.2


def test_agent_checkpoint_manager_save(tmp_path):
    agent = MagicMock()
    agent.episodes_done = 5
    agent.steps_done = 100
    agent.policy_net.state_dict.return_value = {"w": 1}
    agent.optimizer.state_dict.return_value = {"opt": 1}
    agent.hyperparams = {}
    agent.xai_memory = None
    agent.n_observations = 8
    agent.db_manager = MagicMock()

    save_path = str(tmp_path / "agent_test.pth")
    with patch("torch.save") as mock_save, \
         patch("src.utils.paths.get_base_output_dir", return_value=str(tmp_path)):
        AgentCheckpointManager.save(agent, save_path, "ADULT")
        assert mock_save.called
        assert agent.db_manager.sync_file_to_vault.called


def test_agent_checkpoint_manager_load_not_found(tmp_path):
    agent = MagicMock()
    agent.locale_manager.get_string.side_effect = lambda k, **kw: f"mock_{k}"
    agent.db_manager = MagicMock()

    with patch("src.utils.paths.get_base_output_dir", return_value=str(tmp_path)), \
         patch("torch.load", side_effect=FileNotFoundError("missing.pth")):
        maturity = AgentCheckpointManager.load(agent, str(tmp_path / "missing.pth"))
        assert maturity == "CHILD"
        assert agent.db_manager.restore_file_from_vault.called



def test_agent_checkpoint_manager_load_success_and_xai_memory(tmp_path):
    agent = MagicMock()
    agent.device = "cpu"
    agent.n_observations = 8
    agent.locale_manager.get_string.side_effect = lambda k, **kw: f"mock_{k}"

    checkpoint_file = str(tmp_path / "agent.pth")
    with open(checkpoint_file, "w") as f:
        f.write("mock")

    # Mock large xai memory
    mock_mem = MagicMock()
    mock_mem.capacity = 500
    mock_mem.size = 300
    mock_mem.ptr = 300
    mock_mem.states = [torch.zeros((8,)) for _ in range(300)]
    mock_mem.actions = [torch.zeros((1,)) for _ in range(300)]
    mock_mem.rewards = [torch.zeros((1,)) for _ in range(300)]

    dummy_chk = {
        "n_observations": 8,
        "maturity_stage": "ADULT",
        "episodes_done": 12,
        "steps_done": 2000,
        "hyperparameters": {"gamma": 0.99},
        "policy_net_state_dict": {"layer": 1},
        "optimizer_state_dict": {},
        "xai_memory": mock_mem,
    }

    with patch("torch.load", return_value=dummy_chk):
        maturity = AgentCheckpointManager.load(agent, checkpoint_file)
        assert maturity == "ADULT"
        assert agent.episodes_done == 12
        assert agent.steps_done == 2000
        assert agent.policy_net.load_state_dict.called
        assert agent.policy_net.train.called


def test_agent_checkpoint_manager_load_dimension_adaptation(tmp_path):
    agent = MagicMock()
    agent.device = "cpu"
    agent.id = "TL_ADAPT"
    agent.n_observations = 8
    agent.pae_augmentor.latent_dim = 4
    agent.locale_manager.get_string.side_effect = lambda k, **kw: f"mock_{k}"

    checkpoint_file = str(tmp_path / "agent_adapt.pth")
    with open(checkpoint_file, "w") as f:
        f.write("mock")

    # Checkpoint has 6 channels, but current model expects 8 + 4 = 12 channels
    old_weight_v = torch.zeros((16, 6, 3))
    new_weight_v = torch.ones((16, 12, 3))

    agent.policy_net.state_dict.return_value = {
        "tcn.network.0.conv1.weight_v": new_weight_v,
    }

    dummy_chk = {
        "n_observations": 6,
        "maturity_stage": "CHILD",
        "policy_net_state_dict": {
            "tcn.network.0.conv1.weight_v": old_weight_v,
        },
    }

    with patch("torch.load", return_value=dummy_chk):
        maturity = AgentCheckpointManager.load(agent, checkpoint_file)
        assert maturity == "CHILD"
        assert agent._build_network.called
        assert agent.policy_net.load_state_dict.called
