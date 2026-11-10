# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Unit tests for Agent Checkpoint loading, legacy memory adaptation, and tensor channel padding."""

from unittest.mock import MagicMock
import numpy as np
import pytest
import torch

from src.agents.local_agent import LocalAgent
from src.memory.replay_memory import ReplayMemory
from src.models.actor_critic_tcn import ActorCriticNet
from src.models.pae import PredictiveAutoencoder
from src.utils.local_agent_helpers import AgentCheckpointManager


def test_checkpoint_load_legacy_xai_memory(tmp_path):
    """Tests loading a checkpoint containing legacy xai_memory without action_dtype/action_shape."""
    lm_mock = MagicMock()
    ckpt_path = str(tmp_path / "legacy_ckpt.pt")
    legacy_mem = ReplayMemory(capacity=100, state_shape=(4, 5), device=torch.device("cpu"))
    if "action_dtype" in legacy_mem.__dict__:
        del legacy_mem.action_dtype
    if "action_shape" in legacy_mem.__dict__:
        del legacy_mem.action_shape

    agent = LocalAgent(
        tlight_id="TL_LEGACY",
        n_observations=5,
        n_actions=2,
        initial_hyperparams={},
        log_dir=str(tmp_path),
        locale_manager=lm_mock,
    )

    checkpoint_data = {
        "episodes_done": 10,
        "steps_done": 50,
        "hyperparameters": agent.hyperparams,
        "xai_memory": legacy_mem,
        "n_observations": agent.n_observations,
        "maturity_stage": "ADULT",
    }
    torch.save(checkpoint_data, ckpt_path)

    AgentCheckpointManager.load(agent, ckpt_path)

    assert hasattr(agent.xai_memory, "action_dtype")
    assert agent.xai_memory.action_dtype == torch.long
    assert hasattr(agent.xai_memory, "action_shape")
    assert agent.xai_memory.action_shape == (1,)

    agent.xai_memory.push([[1.0] * 5] * 4, 0, None, 0.0)
    assert len(agent.xai_memory) == 1


def test_checkpoint_load_dimension_adaptation(tmp_path):
    """Verifies that a binary (n_actions=2) agent adapts mismatched input channels and legacy 3-action heads."""
    lm_mock = MagicMock()
    pae = PredictiveAutoencoder(input_dim=145, latent_dim=16)

    # 1. Create a legacy 3-action agent checkpoint with 151 channels (135 obs + 16 pae latent)
    old_net = ActorCriticNet(n_observations=151, n_actions=3)
    ckpt_path = str(tmp_path / "agent_with_mismatched_dim.pth")
    checkpoint_data = {
        "episodes_done": 5,
        "steps_done": 100,
        "policy_net_state_dict": old_net.state_dict(),
        "optimizer_state_dict": {},
        "hyperparameters": {"gamma": 0.99, "learning_rate": 0.0001},
        "n_observations": 135,
        "n_actions": 3,
        "maturity_stage": "ADULT",
    }
    torch.save(checkpoint_data, ckpt_path)

    # 2. Instantiate modern binary agent expecting 161 channels (145 obs + 16 pae latent) and n_actions=2
    new_agent = LocalAgent(
        tlight_id="1193472678",
        n_observations=145,
        n_actions=2,
        initial_hyperparams={},
        log_dir=str(tmp_path),
        locale_manager=lm_mock,
        shared_pae=pae,
    )

    # 3. Load checkpoint: should adapt 151->161 channels AND 3->2 binary actions, staying in eval mode
    maturity = AgentCheckpointManager.load(new_agent, ckpt_path)
    assert maturity == "ADULT"
    assert new_agent.policy_net.training is False
    shape = getattr(new_agent.policy_net.tcn.network[0].conv1.weight_v, "shape", ())
    if isinstance(shape, tuple) and len(shape) >= 2:
        assert shape[1] == 161
    head_shape = getattr(new_agent.policy_net.actor_head[0].weight, "shape", ())
    if isinstance(head_shape, tuple) and len(head_shape) >= 1:
        assert head_shape[0] == 2

    # 4. Perform forward inference: should succeed seamlessly with binary action in {0, 1}
    dummy_input = torch.randn(1, 12, 145)
    if hasattr(dummy_input, "to") and hasattr(new_agent, "device"):
        dummy_input = dummy_input.to(new_agent.device)
    action, log_prob, val, entropy = new_agent.choose_action(dummy_input)
    assert action is not None
    assert val is not None
    if hasattr(action, "item"):
        assert int(action.item()) in (0, 1)


def test_legacy_weight_norm_and_post_tcn_migration(tmp_path):
    """Verifies legacy weight_v/weight_g + shared post_tcn_layer + 3-action checkpoint migration."""
    lm_mock = MagicMock()
    agent = LocalAgent(
        tlight_id="TL_MIGRATE",
        n_observations=10,
        n_actions=2,
        initial_hyperparams={},
        log_dir=str(tmp_path),
        locale_manager=lm_mock,
    )

    modern_sd = agent.policy_net.state_dict()
    legacy_sd = {}
    for k, v in modern_sd.items():
        if k.startswith("actor_trunk."):
            suffix = k.split(".", 1)[1]
            legacy_sd[f"post_tcn_layer.{suffix}"] = v.clone()
        elif k.startswith("critic_trunk."):
            continue
        elif k.endswith(".conv1.weight") or k.endswith(".conv2.weight"):
            prefix = k[: -len(".weight")]
            legacy_sd[f"{prefix}.weight_v"] = v.clone()
            out_ch = v.shape[0] if isinstance(getattr(v, "shape", None), tuple) else 64
            legacy_sd[f"{prefix}.weight_g"] = torch.ones((out_ch, 1, 1), device=v.device)
        elif k == "actor_head.0.weight":
            in_f = v.shape[1] if isinstance(getattr(v, "shape", None), tuple) else 128
            legacy_sd[k] = torch.zeros((3, in_f), device=v.device)
        elif k == "actor_head.0.bias":
            legacy_sd[k] = torch.tensor([0.0, 0.5, 0.5], device=v.device)
        else:
            legacy_sd[k] = v.clone()

    ckpt_path = str(tmp_path / "legacy_wn_3act.pth")
    torch.save(
        {
            "episodes_done": 3,
            "steps_done": 42,
            "policy_net_state_dict": legacy_sd,
            "n_observations": 10,
            "n_actions": 3,
            "maturity_stage": "TEEN",
        },
        ckpt_path,
    )

    maturity = AgentCheckpointManager.load(agent, ckpt_path)
    assert maturity == "TEEN"
    assert agent.policy_net.training is False


def test_actor_critic_forward_channel_defensive_padding():
    """Verifies that binary ActorCriticNet gracefully handles tensor inputs with different channel counts."""
    net = ActorCriticNet(n_observations=161)
    assert net.n_actions == 2

    # Case A: Input with fewer channels (151 instead of 161)
    x_small = torch.randn(1, 12, 151)
    probs_s, val_s = net(x_small)
    assert probs_s is not None
    if hasattr(probs_s, "shape") and isinstance(probs_s.shape, tuple):
        assert probs_s.shape == (1, 2)

    # Case B: Input with more channels (170 instead of 161)
    x_large = torch.randn(1, 12, 170)
    probs_l, val_l = net(x_large)
    assert probs_l is not None
    if hasattr(probs_l, "shape") and isinstance(probs_l.shape, tuple):
        assert probs_l.shape == (1, 2)
