# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Sequence padding, temporal standardization, and key-padding mask helpers for PAE."""

from typing import Any, Optional

import torch
import torch.nn as nn
import torch.nn.functional as F


def pad_to_input_dim(x: torch.Tensor, input_dim: int) -> torch.Tensor:
    """Pads or truncates agent local state vectors to the universal PAE `input_dim`."""
    current_dim = x.size(-1)
    if not isinstance(current_dim, int):
        return x
    if current_dim < input_dim:
        return F.pad(x, (0, input_dim - current_dim))
    if current_dim > input_dim:
        return x[..., :input_dim]
    return x


def standardize_sequence(x: torch.Tensor, input_dim: int, history_len: int) -> torch.Tensor:
    """Standardizes 2D `[batch, dim]` or 3D `[batch, seq_len, dim]` inputs to `[batch, history_len, input_dim]`."""
    x_padded = pad_to_input_dim(x, input_dim)

    if x_padded.dim() == 2:
        x_padded = x_padded.unsqueeze(1)

    size_t = x_padded.size()
    if not isinstance(size_t, (tuple, list)) or len(size_t) != 3:
        return x_padded
    _, seq_len, _ = size_t

    if seq_len == history_len:
        return x_padded
    if seq_len < history_len:
        pad_size = history_len - seq_len
        first_frame = x_padded[:, :1, :]
        padding = first_frame.repeat(1, pad_size, 1)
        return torch.cat([padding, x_padded], dim=1)
    return x_padded[:, -history_len:, :]


def build_key_padding_mask(
    batch_size: int,
    orig_dim: int,
    input_dim: int,
    valid_dims: Optional[torch.Tensor],
    device: Any,
) -> Optional[torch.Tensor]:
    """
    Builds boolean mask `[batch_size, input_dim]` where `True` marks zero-padded channels.
    Only constructed on real PyTorch tensors when at least one channel is padded.
    """
    if not isinstance(getattr(nn, "Linear", None), type):
        return None

    if valid_dims is not None:
        v_dims = valid_dims.to(device=device, dtype=torch.long).view(-1)
        if v_dims.numel() == 1 and batch_size > 1:
            v_dims = v_dims.expand(batch_size)
        v_dims = torch.clamp(v_dims, min=1, max=input_dim)
        if bool((v_dims >= input_dim).all()):
            return None
        col_idx = torch.arange(input_dim, device=device).unsqueeze(0)
        return col_idx >= v_dims.unsqueeze(1)

    if isinstance(orig_dim, int) and 0 < orig_dim < input_dim:
        col_idx = torch.arange(input_dim, device=device).unsqueeze(0)
        return (col_idx >= orig_dim).expand(batch_size, input_dim)

    return None
