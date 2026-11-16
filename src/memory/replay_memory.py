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
from typing import Any, Optional

import torch


class ReplayMemory:
    """
    Pre-allocated Prioritized Experience Replay (PER) tensor buffer.
    Stores ring buffers in CPU RAM (optionally pinned for CUDA `non_blocking` minibatch H2D),
    avoiding multi-gigabyte per-agent VRAM reservation while streaming sampled batches onto `device`.
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
        storage_device: Optional[Any] = None,
        pin_memory: Optional[bool] = None,
    ):
        """
        Initializes the buffer pre-allocating contiguous memory chunks with Prioritized Experience Replay (PER).
        """
        self.capacity = capacity
        self.device = device
        self.state_shape = state_shape
        self.action_shape = tuple(action_shape)
        self.action_dtype = action_dtype if action_dtype is not None else getattr(torch, "long", "long")

        # Default backing storage to CPU so per-guardian replay pools do not monopolize VRAM.
        is_real_torch = isinstance(getattr(torch, "device", None), type)
        if storage_device is not None:
            self.storage_device = storage_device
        elif is_real_torch:
            self.storage_device = torch.device("cpu")
        else:
            self.storage_device = device

        target_dev_type = self.device.type if hasattr(self.device, "type") else str(self.device)
        storage_dev_type = (
            self.storage_device.type if hasattr(self.storage_device, "type") else str(self.storage_device)
        )
        can_pin = bool(
            is_real_torch
            and storage_dev_type == "cpu"
            and target_dev_type == "cuda"
            and hasattr(torch, "cuda")
            and torch.cuda.is_available()
        )
        self._pin_memory = bool(can_pin if pin_memory is None else (pin_memory and can_pin))

        # PER Parameters
        self.alpha = alpha
        self.beta = beta
        self.beta_increment = 0.001
        self.eps = 1e-6

        self._init_storage(capacity, pin=self._pin_memory)

    def _init_storage(self, rows: int, pin: bool = False) -> None:
        self.states = self._alloc_buffer((rows, *self.state_shape), dtype=torch.float32, pin=pin)
        self.actions = self._alloc_buffer((rows, *self.action_shape), dtype=self.action_dtype, pin=pin)
        self.next_states = self._alloc_buffer((rows, *self.state_shape), dtype=torch.float32, pin=pin)
        self.rewards = self._alloc_buffer((rows, 1), dtype=torch.float32, pin=pin)
        self.non_final_mask = self._alloc_buffer((rows, 1), dtype=torch.bool, pin=pin)
        self.priorities = torch.zeros((rows,), device=self.storage_device, dtype=torch.float32)
        self.ptr = self.size = 0
        self._max_priority = 1.0

    def _alloc_buffer(self, shape: tuple, dtype: Any, pin: bool = False) -> torch.Tensor:
        tensor = torch.zeros(shape, device=self.storage_device, dtype=dtype)
        if pin and shape[0] > 0 and hasattr(tensor, "pin_memory"):
            try:
                return tensor.pin_memory()
            except Exception:
                self._pin_memory = False
        return tensor

    def _infer_action_dtype(self) -> Any:
        if hasattr(self, "actions") and isinstance(self.actions, torch.Tensor):
            return self.actions.dtype
        return getattr(torch, "long", "long")

    def _infer_action_shape(self) -> tuple:
        if hasattr(self, "actions") and isinstance(self.actions, torch.Tensor) and self.actions.ndim > 1:
            return tuple(self.actions.shape[1:])
        return (1,)

    def __setstate__(self, state: dict) -> None:
        """Ensures backward compatibility when deserializing older ReplayMemory checkpoints."""
        self.__dict__.update(state)
        if "action_dtype" not in self.__dict__:
            self.action_dtype = self._infer_action_dtype()
        if "action_shape" not in self.__dict__:
            self.action_shape = self._infer_action_shape()
        self.__dict__.setdefault("beta_increment", 0.001)
        self.__dict__.setdefault("eps", 1e-6)
        if "storage_device" not in self.__dict__:
            self.storage_device = (
                self.states.device
                if hasattr(getattr(self, "states", None), "device")
                else getattr(self, "device", torch.device("cpu"))
            )
        self.__dict__.setdefault("_pin_memory", False)
        self.__dict__.setdefault("_max_priority", 1.0)

    def __getattr__(self, name: str) -> Any:
        if name == "action_dtype":
            self.action_dtype = self._infer_action_dtype()
            return self.action_dtype
        if name == "action_shape":
            self.action_shape = self._infer_action_shape()
            return self.action_shape
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def _to_storage(self, value: Any, dtype: Any) -> Any:
        if isinstance(value, torch.Tensor):
            t = value.detach() if hasattr(value, "detach") else value
            if hasattr(t, "to") and (
                getattr(t, "device", self.storage_device) != self.storage_device or getattr(t, "dtype", dtype) != dtype
            ):
                return t.to(device=self.storage_device, dtype=dtype)
            return t
        return torch.as_tensor(value, device=self.storage_device, dtype=dtype)

    def _fit_sequence(self, tensor: Any) -> Any:
        """Pads or crops 2D temporal sequences to match `self.state_shape`."""
        if (
            isinstance(tensor, torch.Tensor)
            and hasattr(tensor, "ndim")
            and tensor.ndim == 2
            and len(self.state_shape) == 2
            and tensor.shape[1] == self.state_shape[1]
            and tensor.shape[0] != self.state_shape[0]
        ):
            tgt_len = self.state_shape[0]
            if tensor.shape[0] < tgt_len:
                pad = tensor[:1].repeat(tgt_len - tensor.shape[0], 1)
                return torch.cat([pad, tensor], dim=0)
            return tensor[-tgt_len:]
        return tensor

    def push(self, state, action, next_state, reward):
        """Inserts a transition at the current pointer into storage buffer with cached max priority."""
        if self.capacity <= 0 or getattr(self.states, "numel", lambda: 1)() == 0:
            return
        state_t = self._fit_sequence(self._to_storage(state, torch.float32))
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

        action_t = self._to_storage(action, action_dtype)
        reward_val = [reward] if not isinstance(reward, (torch.Tensor, list, tuple)) else reward
        reward_t = self._to_storage(reward_val, torch.float32)

        self.states[self.ptr] = state_t
        self.actions[self.ptr] = action_t.reshape(action_shape)
        self.rewards[self.ptr] = reward_t.view(1)

        if next_state is not None:
            self.next_states[self.ptr] = self._fit_sequence(self._to_storage(next_state, torch.float32))
            self.non_final_mask[self.ptr] = True
        else:
            self.non_final_mask[self.ptr] = False

        self.priorities[self.ptr] = self._max_priority if self.size > 0 else 1.0
        self.ptr = (self.ptr + 1) % self.capacity
        self.size = min(self.size + 1, self.capacity)

    def boost_last_priority(self, min_priority: float) -> None:
        """Boosts the priority of the most recently pushed transition without dropping cached max."""
        if self.size == 0 or self.capacity <= 0 or getattr(self.priorities, "numel", lambda: 1)() == 0:
            return
        idx = (self.ptr - 1) % self.capacity
        curr = self.priorities[idx]
        curr_val = float(curr.item()) if hasattr(curr, "item") else float(curr)
        new_val = max(curr_val, float(min_priority))
        self.priorities[idx] = new_val
        if new_val > self._max_priority:
            self._max_priority = new_val

    def _move_batch_tensor(self, tensor: Any) -> Any:
        if hasattr(tensor, "device") and tensor.device != self.device and hasattr(tensor, "to"):
            return tensor.to(device=self.device, non_blocking=self._pin_memory)
        return tensor

    def sample(self, batch_size: int) -> Any:
        """
        Prioritized Experience Replay sampling from backing storage, streaming only the sampled
        minibatch onto `self.device` (with `non_blocking` DMA when pinned for CUDA).
        Returns tuple of pre-batched tensors: (states, actions, next_states, non_final_mask, rewards, indices, is_weights)
        """
        if self.size == 0:
            return None

        # 1. Calculate probabilities: p_i = p_i^alpha / sum(p_i^alpha) on storage_device
        valid_priorities = self.priorities[: self.size]
        probs = valid_priorities**self.alpha
        probs_sum = probs.sum()
        if hasattr(probs_sum, "item") and float(probs_sum.item()) > 0.0:
            probs = probs / probs_sum
        elif not hasattr(probs_sum, "item"):
            probs /= probs_sum
        else:
            probs = torch.ones(self.size, device=self.storage_device) / self.size

        # 2. Sample indices on storage_device
        indices = torch.multinomial(probs, batch_size, replacement=True)

        # 3. Calculate Importance Sampling (IS) weights
        self.beta = min(1.0, self.beta + self.beta_increment)

        is_weights = (self.size * probs[indices]) ** (-self.beta)
        max_w = is_weights.max()
        if hasattr(max_w, "item"):
            max_w_val = float(max_w.item())
            if max_w_val > 0.0:
                is_weights = is_weights / max_w_val
        else:
            is_weights /= max_w

        return (
            self._move_batch_tensor(self.states[indices]),
            self._move_batch_tensor(self.actions[indices]),
            self._move_batch_tensor(self.next_states[indices]),
            self._move_batch_tensor(self.non_final_mask[indices].squeeze(1)),
            self._move_batch_tensor(self.rewards[indices].squeeze(1)),
            indices,
            self._move_batch_tensor(is_weights),
        )

    def update_priorities(self, indices: torch.Tensor, td_errors: torch.Tensor):
        """Updates the priorities for the sampled batch based on the TD-Error."""
        idx_loc = indices
        if isinstance(idx_loc, torch.Tensor) and hasattr(idx_loc, "device") and idx_loc.device != self.storage_device:
            idx_loc = idx_loc.detach().to(device=self.storage_device, dtype=torch.long)

        td_loc = td_errors
        if isinstance(td_loc, torch.Tensor):
            td_loc = td_loc.detach().float()
            if hasattr(td_loc, "device") and td_loc.device != self.storage_device:
                td_loc = td_loc.to(device=self.storage_device)

        new_priorities = torch.abs(td_loc) + self.eps
        if isinstance(new_priorities, torch.Tensor) and hasattr(new_priorities, "squeeze"):
            new_priorities = new_priorities.squeeze()
        self.priorities[idx_loc] = new_priorities

        if (
            isinstance(new_priorities, torch.Tensor)
            and type(new_priorities).__name__ != "DummyTensor"
            and new_priorities.numel() > 0
        ):
            batch_max = float(new_priorities.max().item())
            if batch_max > self._max_priority:
                self._max_priority = batch_max

    def release(self) -> None:
        """Releases backing tensor storage on deployment freeze."""
        self._init_storage(0, pin=False)

    def __len__(self) -> int:
        return self.size
