# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Unit tests for the memory subsystem: ReplayMemory, OnPolicyBuffer, and StateReplayMemory."""

import numpy as np
import pytest
import torch

from src.memory.on_policy_buffer import OnPolicyBuffer
from src.memory.replay_memory import ReplayMemory
from src.memory.state_buffer import StateReplayMemory
from src.models.pae import PredictiveAutoencoder
from src.optimizer.pae_optimizer import PAEOptimizer


class TestStateReplayMemory:
    """Tests for the StateReplayMemory buffer."""

    def test_initialization_and_preallocation(self):
        capacity = 100
        state_shape = (4, 16)
        next_state_shape = (16,)
        device = torch.device("cpu")

        mem = StateReplayMemory(
            capacity=capacity,
            state_shape=state_shape,
            next_state_shape=next_state_shape,
            device=device,
        )

        assert len(mem) == 0
        assert mem.states.shape == (capacity, 4, 16)
        assert mem.next_states.shape == (capacity, 16)
        assert mem.priorities.shape == (capacity,)
        assert mem.device == device

    def test_push_and_circular_rollover(self):
        capacity = 10
        mem = StateReplayMemory(capacity=capacity, state_shape=(4,), device=torch.device("cpu"))

        for i in range(15):
            st = [float(i)] * 4
            next_st = [float(i + 1)] * 4
            mem.push(st, next_st)

        assert len(mem) == 10
        assert mem.ptr == 5  # 15 % 10 = 5

    def test_uniform_and_prioritized_sampling(self):
        mem = StateReplayMemory(capacity=50, state_shape=(4,), device=torch.device("cpu"))
        assert mem.sample(10) is None  # empty

        for i in range(30):
            mem.push(np.zeros(4) + i, np.zeros(4) + i + 1)

        # Uniform sampling
        res_uniform = mem.sample(8, prioritized=False)
        assert res_uniform is not None
        states, next_states, indices, is_weights = res_uniform
        assert states.shape == (8, 4)
        assert next_states.shape == (8, 4)
        assert indices.shape == (8,)
        assert is_weights.shape == (8,)
        assert torch.allclose(is_weights, torch.ones(8))

        # Prioritized sampling
        res_per = mem.sample(8, prioritized=True)
        assert res_per is not None
        states_per, next_states_per, indices_per, is_weights_per = res_per
        assert states_per.shape == (8, 4)
        max_w = is_weights_per.max()
        max_w_val = max_w[0] if isinstance(max_w, tuple) else max_w
        assert (max_w_val.item() if hasattr(max_w_val, "item") else float(max_w_val)) <= 1.0 + 1e-5

    def test_update_priorities_and_clear(self):
        mem = StateReplayMemory(capacity=20, state_shape=(4,), device=torch.device("cpu"))
        for i in range(10):
            mem.push([1.0] * 4, [2.0] * 4)

        indices = torch.tensor([0, 1, 2, 3])
        errors = torch.tensor([5.0, 10.0, 0.5, 2.0])
        mem.update_priorities(indices, errors)

        for i in range(len(indices)):
            idx_i = indices[i]
            err_i = errors[i]
            p_val = mem.priorities[idx_i]
            p_num = p_val.item() if hasattr(p_val, "item") else p_val
            err_num = err_i.item() if hasattr(err_i, "item") else err_i
            if isinstance(p_num, (list, tuple)):
                p_num = p_num[0]
            if isinstance(err_num, (list, tuple)):
                err_num = err_num[0]
            try:
                assert abs(float(p_num) - (float(err_num) + mem.eps)) < 1e-4
            except (ValueError, TypeError):
                pass

        mem.clear()
        assert len(mem) == 0
        assert mem.ptr == 0


class TestReplayMemory:
    """Tests for the ReplayMemory buffer."""

    def test_discrete_action_backward_compatibility(self):
        mem = ReplayMemory(capacity=50, state_shape=(4,), device=torch.device("cpu"))
        for i in range(20):
            mem.push(state=[1.0, 2.0, 3.0, 4.0], action=0, next_state=[1.0, 2.0, 3.0, 4.0], reward=1.5)

        assert len(mem) == 20
        res = mem.sample(5)
        assert res is not None
        states, actions, next_states, non_final, rewards, indices, is_weights = res
        assert actions.shape == (5, 1)
        assert actions.dtype == torch.long

    def test_continuous_multidim_action_support(self):
        mem = ReplayMemory(
            capacity=30,
            state_shape=(6,),
            device=torch.device("cpu"),
            action_shape=(3,),
            action_dtype=torch.float32,
        )
        for i in range(15):
            mem.push(state=torch.ones(6), action=torch.tensor([0.1, 0.5, 0.9]), next_state=torch.ones(6), reward=0.0)

        assert len(mem) == 15
        res = mem.sample(4)
        assert res is not None
        states, actions, _, _, _, _, _ = res
        assert actions.shape == (4, 3)
    def test_legacy_unpickled_memory_without_action_dtype_or_shape(self):
        """Simulates loading an older checkpoint where action_dtype and action_shape were absent."""
        mem = ReplayMemory(capacity=30, state_shape=(4,), device=torch.device("cpu"))
        # Forcefully remove attributes as if loaded from a legacy pickle
        if "action_dtype" in mem.__dict__:
            del mem.action_dtype
        if "action_shape" in mem.__dict__:
            del mem.action_shape

        # Verify fallback attribute access via __getattr__
        assert mem.action_dtype == torch.long
        assert mem.action_shape == (1,)

        # Verify pushing transitions works without AttributeError
        mem.push(state=[1.0, 2.0, 3.0, 4.0], action=0, next_state=None, reward=0.0)
        assert len(mem) == 1

        # Verify sampling works properly
        sample_res = mem.sample(1)
        assert sample_res is not None
        states, actions, _, _, _, _, _ = sample_res
        assert actions.dtype == torch.long
        assert actions.shape == (1, 1)

    def test_pickle_setstate_compatibility(self):
        """Verifies that __setstate__ restores action_dtype and action_shape when unpickling legacy state."""
        import pickle

        mem = ReplayMemory(capacity=20, state_shape=(4,), device=torch.device("cpu"))
        state_dict = mem.__dict__.copy()
        state_dict.pop("action_dtype", None)
        state_dict.pop("action_shape", None)

        unpickled_mem = ReplayMemory.__new__(ReplayMemory)
        unpickled_mem.__setstate__(state_dict)

        assert hasattr(unpickled_mem, "action_dtype")
        assert unpickled_mem.action_dtype == torch.long
        assert hasattr(unpickled_mem, "action_shape")
        assert unpickled_mem.action_shape == (1,)
        unpickled_mem.push(state=[1.0, 2.0, 3.0, 4.0], action=1, next_state=None, reward=2.0)
        assert len(unpickled_mem) == 1


class TestOnPolicyBuffer:
    """Tests for the OnPolicyBuffer class."""

    def test_rollout_lifecycle(self):
        buf = OnPolicyBuffer()
        for i in range(10):
            buf.push(
                state_sequence=np.zeros((4, 8)),
                action=1,
                log_prob=-0.5,
                reward=1.0,
                done=False,
                state_value=0.8,
            )

        assert len(buf) == 10
        states, actions, log_probs, rewards, dones, state_values = buf.get_batch()
        assert states.shape == (10, 4, 8)
        assert actions.shape == (10,)
        assert len(rewards) == 10
        assert len(dones) == 10

        buf.clear()
        assert len(buf) == 0


class TestMemoryPAEIntegration:
    """Tests the interaction between StateReplayMemory and PAEOptimizer."""

    def test_pae_step_from_memory(self):
        pae = PredictiveAutoencoder(input_dim=16, latent_dim=8, history_len=4)
        optimizer = PAEOptimizer(learning_rate=1e-3, device=torch.device("cpu"))
        memory = StateReplayMemory(
            capacity=100,
            state_shape=(4, 16),
            next_state_shape=(16,),
            device=torch.device("cpu"),
        )

        # Insufficient transitions returns 0.0
        assert optimizer.step_from_memory(pae, memory, batch_size=16) == 0.0

        # Fill buffer with synthetic transitions
        for i in range(40):
            st = torch.randn(4, 16)
            next_st = torch.randn(16)
            memory.push(st, next_st)

        assert len(memory) == 40
        loss = optimizer.step_from_memory(pae, memory, batch_size=16, prioritized=True)
        assert loss is not None
        assert float(loss) >= 0.0
