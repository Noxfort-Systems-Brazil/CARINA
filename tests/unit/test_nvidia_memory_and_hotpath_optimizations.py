# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Regression tests for Phase 1 NVIDIA GPU/CPU optimizations and hot-path invariants."""

import configparser
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import torch
import torch.nn as nn

from src.agents.guardian_agent import GuardianAgent
from src.engine.fleet_batch_inferencer import FleetBatchInferencer
from src.engine.state_extractor import StateExtractor
from src.engine.strategic_coordinator import StrategicCoordinator
from src.maturity.maturity_manager import Maturity, MaturityManager, resolve_agent_phase
from src.memory.replay_memory import ReplayMemory
from src.memory.state_buffer import StateReplayMemory
from src.optimizer.ppo_optimizer import PPOOptimizer
from src.safety.guardian_checkpoint_service import GuardianCheckpointService
from src.utils.historical_aggregator import HistoricalAggregator

IS_REAL_TORCH = isinstance(getattr(nn, "Linear", None), type)


def test_historical_aggregator_peek_does_not_double_update():
    """Calling peek() computes identical projection without advancing EMAs or SlidingWindowMax."""
    agg_ref = HistoricalAggregator(input_dim=3, window_size=50, short_window=10)
    agg_test = HistoricalAggregator(input_dim=3, window_size=50, short_window=10)

    samples = [
        np.array([0.2, 0.8, 0.1], dtype=np.float32),
        np.array([0.6, 0.4, 0.5], dtype=np.float32),
        np.array([0.9, 0.2, 0.8], dtype=np.float32),
    ]
    for idx, vec in enumerate(samples):
        if idx == 2:
            # Simulates StrategicCoordinator reading mid-step before primary AgentEvaluator.extract_state
            peeked = agg_test.peek(vec)
            assert peeked.shape == (15,)
        out_ref = agg_ref.update(vec)
        out_test = agg_test.update(vec)
        assert np.allclose(out_ref, out_test, atol=1e-6)


def test_resolve_agent_phase_supports_real_manager_and_mocks():
    """resolve_agent_phase uses O(1) lookup on MaturityManager and respects test doubles."""
    lm = MagicMock()
    lm.get_string.side_effect = lambda k, **kw: k
    mgr = MaturityManager(settings={}, locale_manager=lm)
    mgr.register_agents(["TL_1", "TL_2"])
    mgr.set_agent_phase("TL_2", Maturity.ADULT)

    assert resolve_agent_phase(mgr, "TL_1") == Maturity.CHILD
    assert resolve_agent_phase(mgr, "TL_2") == Maturity.ADULT

    mock_mgr = MagicMock()
    mock_mgr.agent_maturity = {"TL_X": Maturity.TEEN}
    assert resolve_agent_phase(mock_mgr, "TL_X") == Maturity.TEEN


@pytest.mark.skipif(not IS_REAL_TORCH, reason="Requires real PyTorch")
def test_state_replay_memory_push_batch_and_cached_max_priority():
    """StateReplayMemory handles push_batch wraparound and avoids .max() scans inside push."""
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    mem = StateReplayMemory(capacity=6, state_shape=(2, 4), next_state_shape=(4,), device=dev)

    states = torch.arange(24, dtype=torch.float32).reshape(3, 2, 4)
    nexts = torch.arange(12, dtype=torch.float32).reshape(3, 4)
    acts = torch.tensor([0, 1, 0], dtype=torch.long)
    vdims = torch.tensor([3, 4, 2], dtype=torch.long)

    mem.push_batch(states, nexts, actions=acts, valid_dims=vdims)
    assert len(mem) == 3
    assert mem.ptr == 3

    # Update priority and confirm subsequent push_batch inherits cached _max_priority
    mem.update_priorities(torch.tensor([1], device=dev), torch.tensor([9.5], device=dev))
    assert mem._max_priority >= 9.5

    # Push 4 more items -> exercises wraparound across capacity 6
    mem.push_batch(torch.ones((4, 2, 4)), torch.ones((4, 4)))
    assert len(mem) == 6
    assert mem.ptr == 1
    assert float(mem.priorities[0].item()) >= 9.5


@pytest.mark.skipif(not IS_REAL_TORCH, reason="Requires real PyTorch")
def test_replay_memory_cpu_storage_and_guardian_freeze_releases_resources(tmp_path):
    """Guardian ReplayMemory backs buffers on CPU and freeze_for_deployment frees training memory."""
    cfg = configparser.ConfigParser()
    cfg["GUARDIAN_AGENT"] = {"batch_size": "4", "memory_size": "16"}
    lm = MagicMock()
    lm.get_string.side_effect = lambda k, default=None, **kw: default or k

    guardian = GuardianAgent(cfg["GUARDIAN_AGENT"], cfg["GUARDIAN_AGENT"], lm, n_observations=4)
    target_dev = guardian.device

    assert guardian.memory.storage_device.type == "cpu"
    assert guardian.memory.states.device.type == "cpu"
    if target_dev.type == "cuda":
        assert guardian.memory._pin_memory is True

    for i in range(6):
        guardian.memory.push(torch.ones(8, 4) * float(i), i % 2, torch.ones(8, 4), float(i))
    guardian.memory.boost_last_priority(4.0)
    assert guardian.memory._max_priority >= 4.0

    batch = guardian.memory.sample(4)
    assert batch is not None
    assert batch[0].device.type == target_dev.type  # Sampled batch arrives on training device

    guardian.freeze_for_deployment()
    assert guardian.is_frozen is True
    assert guardian.target_net is None
    assert guardian.optimizer is None
    assert guardian.neural_predictor.target_net is None
    assert len(guardian.memory) == 0

    # Safe checkpoint save/restore even with frozen None target_net/optimizer
    saved_path = GuardianCheckpointService.save_guardian("TL_F", guardian, checkpoints_dir=str(tmp_path))
    assert saved_path is not None
    # Calling save_all again skips rewriting immutable frozen checkpoint already on disk
    with patch("torch.save") as mock_save:
        GuardianCheckpointService.save_all({"TL_F": guardian}, checkpoints_dir=str(tmp_path))
        assert not mock_save.called

    restored = GuardianAgent(cfg["GUARDIAN_AGENT"], cfg["GUARDIAN_AGENT"], lm, n_observations=4)
    assert GuardianCheckpointService.load_guardian("TL_F", restored, checkpoints_dir=str(tmp_path)) is True
    assert restored.is_frozen is True
    assert restored.target_net is None
    assert restored.optimizer is None
    assert len(restored.memory) == 0
