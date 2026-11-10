# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Defines the ReplayMemory class and its Transition data structure.

This module, extracted from 'guardian_agent.py', implements a replay memory buffer,
a crucial data structure for "off-policy" reinforcement learning algorithms like DQN.
It stores the agent's experiences and allows the sampling of random batches to break
the temporal correlation between samples, stabilizing the training process.
"""
from typing import Any

import torch


class ReplayMemory:
    """
    VRAM-Native Pre-allocated PyTorch Tensor Memory.
    Eliminates PCIe transit bottlenecks for HFT architecture.
    Provides O(1) device-side sampling and zero Python-side looping.
    """

    def __init__(
        self,
        capacity: int,
        state_shape: tuple,
        device: Any,
        alpha: float = 0.6,
        beta: float = 0.4,
        action_shape: tuple = (1,),
        action_dtype: Any = None,
    ):
        """
        Initializes the buffer pre-allocating contiguous memory chunks with Prioritized Experience Replay (PER).
        """
        self.capacity = capacity
        self.device = device
        self.state_shape = state_shape
        self.action_shape = tuple(action_shape)
        self.action_dtype = action_dtype if action_dtype is not None else getattr(torch, "long", "long")

        # PER Parameters
        self.alpha = alpha
        self.beta = beta
        self.beta_increment = 0.001  # Used to anneal beta to 1 over time
        self.eps = 1e-6  # small constant to avoid zero priority

        # Precompute massive tensors mapping directly into GPU Memory (VRAM)
        self.states = torch.zeros((capacity, *state_shape), device=self.device, dtype=torch.float32)
        # Configurable action tensor dimensions and precision
        self.actions = torch.zeros((capacity, *self.action_shape), device=self.device, dtype=self.action_dtype)
        self.next_states = torch.zeros((capacity, *state_shape), device=self.device, dtype=torch.float32)
        self.rewards = torch.zeros((capacity, 1), device=self.device, dtype=torch.float32)

        # Boolean mask to identify non-terminal states
        self.non_final_mask = torch.zeros((capacity, 1), device=self.device, dtype=torch.bool)

        # PER Priorities Array
        self.priorities = torch.zeros((capacity,), device=self.device, dtype=torch.float32)

        self.ptr = 0
        self.size = 0

    def __setstate__(self, state: dict) -> None:
        """
        Ensures backward compatibility when deserializing older ReplayMemory checkpoints.
        """
        self.__dict__.update(state)
        if "action_dtype" not in self.__dict__:
            if hasattr(self, "actions") and isinstance(self.actions, torch.Tensor):
                self.action_dtype = self.actions.dtype
            else:
                self.action_dtype = getattr(torch, "long", "long")
        if "action_shape" not in self.__dict__:
            if hasattr(self, "actions") and isinstance(self.actions, torch.Tensor):
                self.action_shape = tuple(self.actions.shape[1:]) if self.actions.ndim > 1 else (1,)
            else:
                self.action_shape = (1,)
        if "beta_increment" not in self.__dict__:
            self.beta_increment = 0.001
        if "eps" not in self.__dict__:
            self.eps = 1e-6

    def __getattr__(self, name: str) -> Any:
        if name == "action_dtype":
            dtype = (
                self.actions.dtype
                if hasattr(self, "actions") and isinstance(self.actions, torch.Tensor)
                else getattr(torch, "long", "long")
            )
            self.action_dtype = dtype
            return dtype
        if name == "action_shape":
            shape = (
                tuple(self.actions.shape[1:])
                if hasattr(self, "actions") and isinstance(self.actions, torch.Tensor) and self.actions.ndim > 1
                else (1,)
            )
            self.action_shape = shape
            return shape
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def push(self, state, action, next_state, reward):
        """
        Inserts a transition at the current pointer natively into VRAM with max priority.
        Inputs should preferably be PyTorch Tensors already on the device.
        """
        state_t = (
            state if isinstance(state, torch.Tensor) else torch.tensor(state, device=self.device, dtype=torch.float32)
        )
        action_dtype = getattr(self, "action_dtype", None)
        if action_dtype is None:
            action_dtype = (
                self.actions.dtype
                if hasattr(self, "actions") and isinstance(self.actions, torch.Tensor)
                else getattr(torch, "long", "long")
            )
            self.action_dtype = action_dtype

        action_shape = getattr(self, "action_shape", None)
        if action_shape is None:
            action_shape = (
                tuple(self.actions.shape[1:])
                if hasattr(self, "actions") and isinstance(self.actions, torch.Tensor) and self.actions.ndim > 1
                else (1,)
            )
            self.action_shape = action_shape

        if isinstance(action, torch.Tensor):
            action_t = action.to(device=self.device, dtype=action_dtype)
        else:
            action_t = torch.as_tensor(action, device=self.device, dtype=action_dtype)
        reward_t = (
            reward
            if isinstance(reward, torch.Tensor)
            else torch.tensor([reward], device=self.device, dtype=torch.float32)
        )

        if (
            isinstance(state_t, torch.Tensor)
            and hasattr(state_t, "ndim")
            and state_t.ndim == 2
            and len(self.state_shape) == 2
            and state_t.shape[1] == self.state_shape[1]
            and state_t.shape[0] != self.state_shape[0]
        ):
            tgt_len = self.state_shape[0]
            if state_t.shape[0] < tgt_len:
                pad = state_t[:1].repeat(tgt_len - state_t.shape[0], 1)
                state_t = torch.cat([pad, state_t], dim=0)
            else:
                state_t = state_t[-tgt_len:]

        self.states[self.ptr] = state_t
        self.actions[self.ptr] = action_t.reshape(action_shape)
        self.rewards[self.ptr] = reward_t.view(1)

        if next_state is not None:
            next_state_t = (
                next_state
                if isinstance(next_state, torch.Tensor)
                else torch.tensor(next_state, device=self.device, dtype=torch.float32)
            )
            if (
                isinstance(next_state_t, torch.Tensor)
                and hasattr(next_state_t, "ndim")
                and next_state_t.ndim == 2
                and len(self.state_shape) == 2
                and next_state_t.shape[1] == self.state_shape[1]
                and next_state_t.shape[0] != self.state_shape[0]
            ):
                tgt_len = self.state_shape[0]
                if next_state_t.shape[0] < tgt_len:
                    pad = next_state_t[:1].repeat(tgt_len - next_state_t.shape[0], 1)
                    next_state_t = torch.cat([pad, next_state_t], dim=0)
                else:
                    next_state_t = next_state_t[-tgt_len:]
            self.next_states[self.ptr] = next_state_t
            self.non_final_mask[self.ptr] = True
        else:
            self.non_final_mask[self.ptr] = False

        # PER: New transitions are inserted with max priority to guarantee they are sampled at least once
        max_prio = self.priorities.max() if self.size > 0 else 1.0
        self.priorities[self.ptr] = max_prio

        self.ptr = (self.ptr + 1) % self.capacity
        self.size = min(self.size + 1, self.capacity)

    def sample(self, batch_size: int) -> tuple:
        """
        VRAM-Native Prioritized Experience Replay Sampling.
        Returns tuple of pre-batched tensors: (states, actions, next_states, non_final_mask, rewards, indices, is_weights)
        """
        if self.size == 0:
            return None

        # 1. Calculate probabilities: p_i = p_i^alpha / sum(p_i^alpha)
        # Using native VRAM operations for stochastic PER sampling
        valid_priorities = self.priorities[: self.size]
        probs = valid_priorities**self.alpha
        probs /= probs.sum()

        # 2. Sample indices based on probabilities natively on GPU
        indices = torch.multinomial(probs, batch_size, replacement=True)

        # 3. Calculate Importance Sampling (IS) weights
        # w_i = (N * P(i)) ^ -beta
        # Normalize weights by max weight for stability
        self.beta = min(1.0, self.beta + self.beta_increment)

        is_weights = (self.size * probs[indices]) ** (-self.beta)
        is_weights /= is_weights.max()  # Normalize

        return (
            self.states[indices],
            self.actions[indices],
            self.next_states[indices],
            self.non_final_mask[indices].squeeze(1),
            self.rewards[indices].squeeze(1),
            indices,
            is_weights,
        )

    def update_priorities(self, indices: torch.Tensor, td_errors: torch.Tensor):
        """
        Updates the priorities for the sampled batch based on the TD-Error.
        """
        # Absolute TD-error + epsilon (to avoid 0 probability)
        new_priorities = torch.abs(td_errors) + self.eps
        # Clip max priority to avoid extreme spikes (optional but safe)
        self.priorities[indices] = new_priorities.detach().float()

    def __len__(self) -> int:
        return self.size
