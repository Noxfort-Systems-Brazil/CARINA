# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# File: tests/unit/test_engine_optimizers.py
# Author: Gabriel Moraes
# Date: September 2026

from unittest.mock import MagicMock

import pytest
import torch

from engine.dqn_optimizer import DQNOptimizer
from engine.ppo_optimizer import PPOOptimizer


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
