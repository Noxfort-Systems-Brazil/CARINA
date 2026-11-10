# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Defines the StateReplayMemory buffer for self-supervised and action-conditioned world models.

Provides a VRAM-native, contiguous pre-allocated circular buffer storing
`(state_t, next_state_{t+1})` transitions alongside optional binary `action_t`
(`0 = ADVANCE`, `1 = KEEP`, `-1 = unconditioned`) and `valid_dim` (number of active
non-padded intersection channels) for masked loss computation.
"""

from typing import Optional, Tuple, Union

import numpy as np
import torch


class StateReplayMemory:
    """
    VRAM-Native Pre-allocated PyTorch Tensor Memory for State Transitions.
    Optimized for self-supervised / action-conditioned predictive models (PAE, GNNs).
    """

    def __init__(
        self,
        capacity: int,
        state_shape: tuple,
        next_state_shape: Optional[tuple] = None,
        device: Optional[torch.device] = None,
        alpha: float = 0.6,
        beta: float = 0.4,
        beta_increment: float = 0.001,
    ) -> None:
        self.capacity = int(capacity)
        self.state_shape = tuple(state_shape)
        self.next_state_shape = tuple(next_state_shape) if next_state_shape is not None else self.state_shape
        if isinstance(getattr(torch, "device", None), type):
            self.device = device if isinstance(device, (torch.device, str)) else torch.device("cpu")
        else:
            self.device = device or torch.device("cpu")

        self.alpha = float(alpha)
        self.beta = float(beta)
        self.beta_increment = float(beta_increment)
        self.eps = 1e-6

        default_feat_dim = int(self.next_state_shape[-1]) if len(self.next_state_shape) > 0 else 1

        self.states = torch.zeros((self.capacity, *self.state_shape), device=self.device, dtype=torch.float32)
        self.next_states = torch.zeros(
            (self.capacity, *self.next_state_shape), device=self.device, dtype=torch.float32
        )
        self.actions = torch.full((self.capacity,), -1, device=self.device, dtype=torch.long)
        self.valid_dims = torch.full((self.capacity,), default_feat_dim, device=self.device, dtype=torch.long)
        self.priorities = torch.zeros((self.capacity,), device=self.device, dtype=torch.float32)

        self.ptr = 0
        self.size = 0

    def push(
        self,
        state: Union[torch.Tensor, np.ndarray, list],
        next_state: Union[torch.Tensor, np.ndarray, list],
        priority: Optional[float] = None,
        action: Optional[int] = None,
        valid_dim: Optional[int] = None,
    ) -> None:
        """
        Inserts a transition `(state, next_state)` with optional binary `action` and `valid_dim`.
        """
        if isinstance(state, torch.Tensor):
            state_t = state.to(device=self.device, dtype=torch.float32)
        else:
            state_t = torch.as_tensor(state, device=self.device, dtype=torch.float32)

        if isinstance(next_state, torch.Tensor):
            next_state_t = next_state.to(device=self.device, dtype=torch.float32)
        else:
            next_state_t = torch.as_tensor(next_state, device=self.device, dtype=torch.float32)

        if state_t.shape != self.state_shape and state_t.squeeze(0).shape == self.state_shape:
            state_t = state_t.squeeze(0)
        if next_state_t.shape != self.next_state_shape and next_state_t.squeeze(0).shape == self.next_state_shape:
            next_state_t = next_state_t.squeeze(0)

        if (
            isinstance(state_t, torch.Tensor)
            and hasattr(state_t, "dim")
            and state_t.dim() == 2
            and len(self.state_shape) == 2
            and state_t.shape != self.state_shape
        ):
            tgt_seq, tgt_feat = self.state_shape
            if state_t.size(1) < tgt_feat:
                state_t = torch.nn.functional.pad(state_t, (0, tgt_feat - state_t.size(1)))
            elif state_t.size(1) > tgt_feat:
                state_t = state_t[:, :tgt_feat]
            if state_t.size(0) < tgt_seq:
                pad_frames = state_t[:1].expand(tgt_seq - state_t.size(0), -1)
                state_t = torch.cat([pad_frames, state_t], dim=0)
            elif state_t.size(0) > tgt_seq:
                state_t = state_t[-tgt_seq:]

        if (
            isinstance(next_state_t, torch.Tensor)
            and hasattr(next_state_t, "dim")
            and next_state_t.dim() == 1
            and len(self.next_state_shape) == 1
            and next_state_t.shape != self.next_state_shape
        ):
            tgt_feat = self.next_state_shape[0]
            if next_state_t.size(0) < tgt_feat:
                next_state_t = torch.nn.functional.pad(next_state_t, (0, tgt_feat - next_state_t.size(0)))
            elif next_state_t.size(0) > tgt_feat:
                next_state_t = next_state_t[:tgt_feat]

        self.states[self.ptr] = state_t
        self.next_states[self.ptr] = next_state_t
        self.actions[self.ptr] = int(action) if action is not None else -1
        inferred_valid = int(valid_dim) if valid_dim is not None else int(self.next_state_shape[-1])
        self.valid_dims[self.ptr] = max(1, inferred_valid)

        if priority is not None:
            self.priorities[self.ptr] = float(priority)
        else:
            if self.size > 0:
                p_max = self.priorities[: self.size].max()
                if isinstance(p_max, tuple):
                    p_max = p_max[0]
                max_prio = p_max.item() if hasattr(p_max, "item") else float(p_max)
            else:
                max_prio = 1.0
            self.priorities[self.ptr] = max_prio

        self.ptr = (self.ptr + 1) % self.capacity
        self.size = min(self.size + 1, self.capacity)

    def sample(
        self, batch_size: int, prioritized: bool = True, include_metadata: bool = False
    ) -> Optional[Tuple[torch.Tensor, ...]]:
        """
        Samples a batch of transitions.
        Returns `(states, next_states, indices, is_weights)` by default, or
        `(states, next_states, indices, is_weights, actions, valid_dims)` when `include_metadata=True`.
        """
        if self.size < batch_size or self.size == 0:
            return None

        if prioritized:
            valid_priorities = self.priorities[: self.size]
            probs = valid_priorities**self.alpha
            sum_probs = probs.sum()
            if sum_probs > 0:
                probs = probs / sum_probs
            else:
                probs = torch.ones(self.size, device=self.device) / self.size

            indices = torch.multinomial(probs, batch_size, replacement=True)

            self.beta = min(1.0, self.beta + self.beta_increment)
            is_weights = (self.size * probs[indices]) ** (-self.beta)
            max_weight = is_weights.max()
            if isinstance(max_weight, tuple):
                max_weight = max_weight[0]
            if max_weight > 0:
                is_weights = is_weights / max_weight
            else:
                is_weights = torch.ones_like(is_weights)
        else:
            indices = torch.randint(0, self.size, (batch_size,), device=self.device)
            is_weights = torch.ones(batch_size, device=self.device, dtype=torch.float32)

        if include_metadata:
            return (
                self.states[indices],
                self.next_states[indices],
                indices,
                is_weights,
                self.actions[indices],
                self.valid_dims[indices],
            )

        return (
            self.states[indices],
            self.next_states[indices],
            indices,
            is_weights,
        )

    def update_priorities(self, indices: torch.Tensor, errors: torch.Tensor) -> None:
        """Updates PER priorities based on per-sample prediction error."""
        new_priorities = torch.abs(errors) + self.eps
        self.priorities[indices] = new_priorities.detach().float().squeeze()

    def clear(self) -> None:
        """Clears all stored transitions in the buffer."""
        self.ptr = 0
        self.size = 0
        self.states.zero_()
        self.next_states.zero_()
        self.actions.fill_(-1)
        self.priorities.zero_()

    def __len__(self) -> int:
        return self.size
