# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from unittest.mock import MagicMock

import pytest
import torch

from optimizer.dqn_optimizer import DQNOptimizer
from optimizer.ppo_optimizer import PPOOptimizer


def test_dqn_optimizer_initialization():
    """DQNOptimizer parses hyperparameters and handles short replay memory."""
    device = torch.device("cpu")
    hyperparams = {"gamma": 0.95, "batch_size": 64}

    optimizer = DQNOptimizer(hyperparams, device)
    assert optimizer.gamma == 0.95
    assert optimizer.batch_size == 64

    # When memory has fewer transitions than batch_size, step returns 0.0
    memory = [1, 2, 3]  # < 64
    loss = optimizer.step(
        policy_net=MagicMock(),
        target_net=MagicMock(),
        optimizer=MagicMock(),
        memory=memory,
        forward_policy=MagicMock(),
        forward_target=MagicMock(),
    )
    assert loss == 0.0


def test_dqn_optimizer_reload_hyperparameters():
    """DQNOptimizer updates parameters in-place without reconstruction."""
    optimizer = DQNOptimizer({}, torch.device("cpu"))
    assert optimizer.gamma == 0.90
    assert optimizer.batch_size == 128

    optimizer.load_hyperparameters({"gamma": 0.88, "batch_size": 32})
    assert optimizer.gamma == 0.88
    assert optimizer.batch_size == 32


def test_ppo_optimizer_initialization():
    """PPOOptimizer sets up RL parameters for Generalized Advantage Estimation."""
    device = torch.device("cpu")
    hyperparams = {
        "gamma": 0.98,
        "gae_lambda": 0.90,
        "eps_clip": 0.15,
        "k_epochs": 5,
        "target_kl": 0.015,
        "grad_clip_norm": 0.4,
    }

    optimizer = PPOOptimizer(hyperparams, device)
    assert optimizer.gamma == 0.98
    assert optimizer.gae_lambda == 0.90
    assert optimizer.eps_clip == 0.15
    assert optimizer.k_epochs == 5
    assert optimizer.target_kl == 0.015
    assert optimizer.grad_clip_norm == 0.4


def test_ppo_optimizer_reload_hyperparameters():
    """PPOOptimizer can reload hyperparameters dynamically."""
    optimizer = PPOOptimizer({}, torch.device("cpu"))
    assert optimizer.gamma == 0.99
    assert optimizer.k_epochs == 4

    optimizer.load_hyperparameters({"gamma": 0.92, "k_epochs": 2})
    assert optimizer.gamma == 0.92
    assert optimizer.k_epochs == 2


def test_ppo_optimizer_step_execution():
    """PPOOptimizer executes step successfully, ensuring states are placed on the optimizer device."""
    device = torch.device("cuda" if hasattr(torch, "cuda") and torch.cuda.is_available() else "cpu")
    scaler = None
    if hasattr(torch, "amp") and hasattr(torch.amp, "GradScaler"):
        scaler = torch.amp.GradScaler(enabled=(device.type == "cuda"))

    optimizer = PPOOptimizer({"k_epochs": 2}, device=device, scaler=scaler)

    batch_size = 4
    seq_len = 4
    obs_dim = 10

    if hasattr(torch, "nn") and hasattr(torch.nn, "Linear") and isinstance(torch.nn.Linear, type):
        policy_net = torch.nn.Linear(obs_dim, 2).to(device)
        opt = torch.optim.Adam(policy_net.parameters(), lr=1e-3)
    else:
        policy_net = MagicMock()
        policy_net.parameters.return_value = [torch.zeros(1, requires_grad=True)] if hasattr(torch, "zeros") else []
        opt = MagicMock()

    # Old states provided on CPU as returned by OnPolicyBuffer
    if hasattr(torch, "randn"):
        old_states = torch.randn(batch_size, seq_len, obs_dim, device="cpu")
        old_actions = torch.zeros(batch_size, dtype=torch.long, device="cpu")
        old_log_probs = torch.zeros(batch_size, dtype=torch.float32, device="cpu")
        rewards = [1.0] * batch_size
        dones = [False] * batch_size
        old_state_values = torch.zeros(batch_size, dtype=torch.float32, device="cpu")
    else:
        old_states = MagicMock()
        old_actions = MagicMock()
        old_log_probs = MagicMock()
        rewards = [1.0] * batch_size
        dones = [False] * batch_size
        old_state_values = MagicMock()

    memory_batch = (old_states, old_actions, old_log_probs, rewards, dones, old_state_values)

    evaluated_states_device = []

    def evaluate_fn(states, actions):
        if hasattr(states, "device"):
            dev_type = states.device.type if hasattr(states.device, "type") else str(states.device)
            evaluated_states_device.append(dev_type)
        if hasattr(torch, "zeros") and callable(policy_net):
            out = policy_net(states[:, -1, :])
            log_prob = out[:, 0]
            val = out[:, 1]
            entropy = torch.zeros(batch_size, device=device)
            return log_prob, val, entropy
        return MagicMock(), MagicMock(), MagicMock()

    loss = optimizer.step(
        policy_net=policy_net,
        optimizer=opt,
        memory_batch=memory_batch,
        evaluate_fn=evaluate_fn,
    )

    assert isinstance(loss, (float, int)) or hasattr(loss, "_mock_name")
    if hasattr(torch, "randn"):
        expected_dev = device.type if hasattr(device, "type") else str(device)
        assert evaluated_states_device[0] == expected_dev


def test_optimizers_scaler_auto_detection():
    """Verifies that DQNOptimizer and PPOOptimizer automatically configure GradScaler based on device."""
    cpu_device = torch.device("cpu")
    dqn_cpu = DQNOptimizer({}, cpu_device)
    ppo_cpu = PPOOptimizer({}, cpu_device)

    assert dqn_cpu.scaler.is_enabled() is False
    assert ppo_cpu.scaler.is_enabled() is False

    if torch.cuda.is_available():
        cuda_device = torch.device("cuda")
        dqn_cuda = DQNOptimizer({}, cuda_device)
        ppo_cuda = PPOOptimizer({}, cuda_device)
        assert dqn_cuda.scaler.is_enabled() is True
        assert ppo_cuda.scaler.is_enabled() is True


