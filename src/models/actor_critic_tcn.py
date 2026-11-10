# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import Any, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

from src.models.tcn_backbone import (
    Chomp1d,
    TemporalAttentionPool,
    TemporalBlock,
    TemporalConvNet,
    align_tcn_input_channels,
    init_orthogonal,
)

__all__ = ["Chomp1d", "TemporalBlock", "TemporalConvNet", "ActorCriticNet"]


class ActorCriticNet(nn.Module):
    """
    Modernized Tactical Actor-Critic Network for CARINA's binary stage controller:
    - Binary action space (`n_actions = 2`: `0 = ADVANCE / CHANGE_STAGE`, `1 = KEEP / HOLD`).
    - Unified causal TCN (`num_levels = 3` covering full `sequence_length = 12` horizon)
      followed by `TemporalAttentionPool`.
    - Decoupled Actor and Critic post-TCN trunks with orthogonal initialization
      (`gain = 0.01` on the policy head, `gain = 1.0` on the value head).
    - Emits raw FP32 logits via `forward_logits` (+ physical `action_mask`) for
      AMP-safe `Categorical(logits=...)` without Softmax underflow.
    """

    outputs_logits: bool = True

    def __init__(
        self,
        n_observations: int,
        n_actions: int = 2,
        hidden_size: int = 128,
        dropout_p: float = 0.1,
        num_levels: int = 3,
    ) -> None:
        super().__init__()
        self.n_observations = int(n_observations)
        self.n_actions = int(n_actions)
        self.hidden_size = int(hidden_size)
        self.dropout_p = float(dropout_p)

        num_channels = [self.hidden_size] * max(1, int(num_levels))
        kernel_size = 3

        self.tcn = TemporalConvNet(
            self.n_observations, num_channels, kernel_size=kernel_size, dropout=self.dropout_p
        )
        self.temporal_pool = TemporalAttentionPool(self.hidden_size, dropout=self.dropout_p)

        # Decoupled Actor and Critic feature trunks (prevents critic gradient interference)
        actor_fc = nn.Linear(self.hidden_size, self.hidden_size)
        critic_fc = nn.Linear(self.hidden_size, self.hidden_size)
        init_orthogonal(actor_fc, gain=1.41421356)
        init_orthogonal(critic_fc, gain=1.41421356)

        self.actor_trunk = nn.Sequential(
            actor_fc,
            nn.LayerNorm(self.hidden_size),
            nn.SiLU(),
            nn.Dropout(self.dropout_p),
        )
        self.critic_trunk = nn.Sequential(
            critic_fc,
            nn.LayerNorm(self.hidden_size),
            nn.SiLU(),
            nn.Dropout(self.dropout_p),
        )

        # Raw logit Actor Head (no Softmax inside AMP!) and Value Critic Head
        actor_out = nn.Linear(self.hidden_size, self.n_actions)
        critic_out = nn.Linear(self.hidden_size, 1)
        init_orthogonal(actor_out, gain=0.01)
        init_orthogonal(critic_out, gain=1.0)

        self.actor_head = nn.Sequential(actor_out)
        self.critic_head = nn.Sequential(critic_out)

    @staticmethod
    def apply_action_mask(logits: torch.Tensor, action_mask: Optional[torch.Tensor]) -> torch.Tensor:
        """
        Applies a physical boolean/0-1 mask (`True`/`1` = allowed, `False`/`0` = forbidden)
        to raw FP32 action logits, guaranteeing at least one valid action per batch element.
        """
        logits_fp32 = logits.float() if hasattr(logits, "float") else logits
        if action_mask is None:
            return logits_fp32

        try:
            mask = action_mask
            if not isinstance(mask, torch.Tensor) and type(mask).__name__ != "DummyTensor":
                mask = torch.as_tensor(mask, dtype=torch.bool, device=getattr(logits_fp32, "device", "cpu"))
            if hasattr(mask, "to") and hasattr(logits_fp32, "device") and getattr(mask, "device", None) != logits_fp32.device:
                mask = mask.to(logits_fp32.device)
            if hasattr(mask, "dim") and mask.dim() == 1 and hasattr(logits_fp32, "dim") and logits_fp32.dim() == 2:
                mask = mask.unsqueeze(0).expand(logits_fp32.size(0), -1)
            mask_bool = mask.bool() if hasattr(mask, "bool") else mask

            # Safety fallback: if all actions in a row were masked out, allow KEEP (index 1 or last index)
            if isinstance(logits_fp32, torch.Tensor) and isinstance(mask_bool, torch.Tensor):
                any_valid = mask_bool.any(dim=-1, keepdim=True)
                fallback = torch.zeros_like(mask_bool)
                fallback_idx = 1 if mask_bool.size(-1) > 1 else 0
                fallback[..., fallback_idx] = True
                safe_mask = torch.where(any_valid, mask_bool, fallback)
                return logits_fp32.masked_fill(~safe_mask, -1e9)
        except Exception:
            pass

        return logits_fp32

    def forward_logits(
        self,
        state_sequence: torch.Tensor,
        action_mask: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Computes `(masked_logits_fp32, state_value)` from `[batch_size, seq_len, n_observations]`.
        """
        param = next(self.parameters(), None)
        if (
            param is not None
            and hasattr(state_sequence, "device")
            and hasattr(state_sequence, "to")
            and getattr(param, "device", None) is not None
            and state_sequence.device != param.device
        ):
            state_sequence = state_sequence.to(param.device)

        if hasattr(state_sequence, "dim") and state_sequence.dim() == 2:
            state_sequence = state_sequence.unsqueeze(1)

        # Transpose [batch, seq, obs] -> [batch, obs, seq]
        x = state_sequence.transpose(1, 2)
        x = align_tcn_input_channels(x, self.tcn)

        y = self.tcn(x)
        temporal_context = self.temporal_pool(y)

        actor_features = self.actor_trunk(temporal_context)
        critic_features = self.critic_trunk(temporal_context)

        raw_logits = self.actor_head(actor_features)
        masked_logits = self.apply_action_mask(raw_logits, action_mask)
        state_value = self.critic_head(critic_features)
        state_value_fp32 = state_value.float() if hasattr(state_value, "float") else state_value

        return masked_logits, state_value_fp32

    def forward(
        self,
        state_sequence: torch.Tensor,
        action_mask: Optional[torch.Tensor] = None,
        return_logits: bool = False,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass returning `(action_probs, state_value)` by default for backward compatibility,
        or `(action_logits, state_value)` when `return_logits=True`.
        """
        logits, state_value = self.forward_logits(state_sequence, action_mask=action_mask)
        if return_logits:
            return logits, state_value
        return F.softmax(logits, dim=-1), state_value

    def optimize_engine(self, enable_compile: bool = True, mode: str = "reduce-overhead") -> None:
        """Optionally compiles the causal TCN backbone via PyTorch 2.x `torch.compile`."""
        if not enable_compile or not hasattr(torch, "compile"):
            return
        try:
            self.tcn = torch.compile(self.tcn, mode=mode)  # type: ignore[assignment]
        except Exception as e:
            logging.warning(f"[ActorCriticNet] torch.compile fallback to eager mode: {e}", exc_info=True)
