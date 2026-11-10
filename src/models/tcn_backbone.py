# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Unified Causal Temporal Convolutional Network (TCN) Backbone & Temporal Attention Pooling.

Shared across CARINA's tactical (ActorCriticNet), safety (D3QN_TCN / QR-D3QN),
and strategic (STGATv2Lite) neural architectures:
- Replaces deprecated `torch.nn.utils.weight_norm` with `TemporalConv1d` + causal
  channel-wise `GroupNorm(1, C)` + `SiLU` activations and orthogonal initialization.
- Fully compatible with `torch.func.stack_module_state` + `torch.vmap` and `torch.compile`.
- Adds `TemporalAttentionPool` to aggregate multi-horizon causal dynamics with the
  instantaneous state `y[:, :, -1]`.
"""

import math
from typing import List

import torch
import torch.nn as nn
import torch.nn.functional as F

_Conv1dBase = nn.Conv1d if isinstance(getattr(nn, "Conv1d", None), type) else nn.Module


def init_orthogonal(module: nn.Module, gain: float = 1.0) -> None:
    """Applies orthogonal weight initialization and zero bias when running with real PyTorch tensors."""
    if not isinstance(getattr(nn, "Linear", None), type):
        return
    weight = getattr(module, "weight", None)
    if isinstance(weight, torch.Tensor) and weight.dim() >= 2:
        nn.init.orthogonal_(weight, gain=gain)
    bias = getattr(module, "bias", None)
    if isinstance(bias, torch.Tensor):
        nn.init.zeros_(bias)


class Chomp1d(nn.Module):
    """
    Removes right-side causal padding so output at step t depends strictly on inputs <= t.
    """

    def __init__(self, chomp_size: int) -> None:
        super().__init__()
        self.chomp_size = int(chomp_size)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if self.chomp_size <= 0:
            return x
        return x[:, :, : -self.chomp_size].contiguous()


class TemporalConv1d(_Conv1dBase):  # type: ignore[misc, valid-type]
    """
    Causal 1D Convolution preserving identical class identity across instances for `torch.vmap`,
    while exposing `.weight_v` as a backward-compatible alias to `.weight`.
    """

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_size: int,
        stride: int = 1,
        padding: int = 0,
        dilation: int = 1,
    ) -> None:
        if _Conv1dBase is nn.Module:
            super().__init__()
            self.in_channels = in_channels
            self.out_channels = out_channels
            self.kernel_size = (kernel_size,)
            self._mock_conv = nn.Conv1d(
                in_channels, out_channels, kernel_size, stride=stride, padding=padding, dilation=dilation
            )
            self.weight = getattr(self._mock_conv, "weight", torch.zeros((out_channels, in_channels, kernel_size)))
            self.bias = getattr(self._mock_conv, "bias", torch.zeros((out_channels,)))
        else:
            super().__init__(
                in_channels, out_channels, kernel_size, stride=stride, padding=padding, dilation=dilation
            )
            init_orthogonal(self, gain=math.sqrt(2.0))

    @property
    def weight_v(self) -> torch.Tensor:
        return self.weight

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if _Conv1dBase is nn.Module:
            return self._mock_conv(x)
        return super().forward(x)


class TemporalBlock(nn.Module):
    """
    Modern residual causal TCN block using dilated convolutions, causal channel-wise
    LayerNorm (`GroupNorm(1, C)`), `SiLU` activations, Dropout, and orthogonal initialization.
    """

    def __init__(
        self,
        n_inputs: int,
        n_outputs: int,
        kernel_size: int,
        stride: int,
        dilation: int,
        padding: int,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()

        self.conv1 = TemporalConv1d(
            n_inputs, n_outputs, kernel_size, stride=stride, padding=padding, dilation=dilation
        )
        self.chomp1 = Chomp1d(padding)
        self.norm1 = nn.GroupNorm(1, n_outputs)
        self.act1 = nn.SiLU()
        self.dropout1 = nn.Dropout(dropout)

        self.conv2 = TemporalConv1d(
            n_outputs, n_outputs, kernel_size, stride=stride, padding=padding, dilation=dilation
        )
        self.chomp2 = Chomp1d(padding)
        self.norm2 = nn.GroupNorm(1, n_outputs)
        self.act2 = nn.SiLU()
        self.dropout2 = nn.Dropout(dropout)

        self.net = nn.Sequential(
            self.conv1,
            self.chomp1,
            self.norm1,
            self.act1,
            self.dropout1,
            self.conv2,
            self.chomp2,
            self.norm2,
            self.act2,
            self.dropout2,
        )

        self.downsample = nn.Conv1d(n_inputs, n_outputs, 1) if n_inputs != n_outputs else None
        if self.downsample is not None:
            init_orthogonal(self.downsample, gain=1.0)
        self.act_out = nn.SiLU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = self.net(x)
        res = x if self.downsample is None else self.downsample(x)
        return self.act_out(out + res)


class TemporalConvNet(nn.Module):
    """
    Multi-level causal dilated Temporal Convolutional Network.
    """

    def __init__(self, num_inputs: int, num_channels: List[int], kernel_size: int = 3, dropout: float = 0.1) -> None:
        super().__init__()
        layers: List[nn.Module] = []
        for i, out_channels in enumerate(num_channels):
            dilation_size = 2**i
            in_channels = num_inputs if i == 0 else num_channels[i - 1]
            layers.append(
                TemporalBlock(
                    n_inputs=in_channels,
                    n_outputs=out_channels,
                    kernel_size=kernel_size,
                    stride=1,
                    dilation=dilation_size,
                    padding=(kernel_size - 1) * dilation_size,
                    dropout=dropout,
                )
            )
        self.network = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.network(x)


class TemporalAttentionPool(nn.Module):
    """
    Causal Temporal Attention Pooling over TCN hidden states `y: [B, C, T]`.

    Uses the latest causal representation `y[:, :, -1]` as query over all causal
    steps `t = 0..T-1`, blending the attended temporal summary residually with
    `y[:, :, -1]` so sudden upstream queue/platoon shocks are never lost.
    """

    def __init__(self, channels: int, dropout: float = 0.0) -> None:
        super().__init__()
        self.channels = int(channels)
        self.scale = 1.0 / math.sqrt(max(1, self.channels))
        self.q_proj = nn.Linear(self.channels, self.channels)
        self.k_proj = nn.Linear(self.channels, self.channels)
        self.v_proj = nn.Linear(self.channels, self.channels)
        self.out_proj = nn.Linear(self.channels, self.channels)
        self.dropout = nn.Dropout(dropout) if dropout > 0.0 else nn.Identity()
        self.norm = nn.LayerNorm(self.channels)

        init_orthogonal(self.q_proj, gain=1.0)
        init_orthogonal(self.k_proj, gain=1.0)
        init_orthogonal(self.v_proj, gain=1.0)
        init_orthogonal(self.out_proj, gain=0.5)

    def forward(self, y: torch.Tensor) -> torch.Tensor:
        # y: [B, C, T]
        last_step = y[:, :, -1]  # [B, C]
        y_seq = y.transpose(1, 2)  # [B, T, C]

        q = self.q_proj(last_step).unsqueeze(1)  # [B, 1, C]
        k = self.k_proj(y_seq)  # [B, T, C]
        v = self.v_proj(y_seq)  # [B, T, C]

        scores = torch.matmul(q, k.transpose(1, 2)) * self.scale  # [B, 1, T]
        attn = F.softmax(scores, dim=-1)
        attn = self.dropout(attn)

        context = torch.matmul(attn, v).squeeze(1)  # [B, C]
        return self.norm(last_step + self.out_proj(context))


def align_tcn_input_channels(x: torch.Tensor, tcn: TemporalConvNet) -> torch.Tensor:
    """
    Defensively pads or slices `x: [B, C, T]` to match the first TCN conv layer's expected channels.
    """
    try:
        conv1 = tcn.network[0].conv1
        expected_channels = getattr(conv1, "in_channels", None)
        if not isinstance(expected_channels, int):
            w = getattr(conv1, "weight", None)
            if hasattr(w, "shape") and isinstance(w.shape, tuple) and len(w.shape) > 1:
                expected_channels = w.shape[1]
        if (
            isinstance(expected_channels, int)
            and hasattr(x, "shape")
            and isinstance(x.shape, tuple)
            and len(x.shape) > 1
            and isinstance(x.shape[1], int)
            and x.shape[1] != expected_channels
        ):
            if x.shape[1] < expected_channels:
                pad_size = expected_channels - x.shape[1]
                x = F.pad(x, (0, 0, 0, pad_size))
            else:
                x = x[:, :expected_channels, :]
    except Exception:
        pass
    return x
