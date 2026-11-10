# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Distributional Dueling Double DQN (QR-D3QN) with Unified Causal TCN Backbone,
Temporal Attention Pooling, and Universal PAE Latent Fusion.

Designed for CARINA's Neuro-Symbolic Guardian Agent:
- Models the full return distribution over `num_quantiles` (default 32) per binary
  safety action (`0 = KEEP_STAGE`, `1 = CHANGE_STAGE`), enabling tail-risk CVaR
  spillback protection in `GuardianNeuralPredictor`.
- `forward()` returns the expectation `q_quantiles.mean(dim=-1)` `[B, n_actions]`
  for 100% drop-in compatibility with standard Q-value callers.
"""

from typing import List, Optional

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

__all__ = ["Chomp1d", "TemporalBlock", "TemporalConvNet", "D3QN_TCN"]


class D3QN_TCN(nn.Module):
    """
    Distributional Dueling Double DQN (`QR-D3QN`) with causal TCN + `TemporalAttentionPool`
    and PAE latent fusion.
    """

    is_distributional: bool = True

    def __init__(
        self,
        n_observations: int = 2,
        n_actions: int = 2,
        pae_latent_dim: int = 16,
        hidden_size: int = 64,
        tcn_channels: Optional[List[int]] = None,
        kernel_size: int = 3,
        dropout: float = 0.1,
        num_quantiles: int = 32,
    ) -> None:
        super().__init__()

        if tcn_channels is None:
            tcn_channels = [hidden_size, hidden_size, hidden_size]

        self.n_observations = int(n_observations)
        self.n_actions = int(n_actions)
        self.pae_latent_dim = int(pae_latent_dim)
        self.hidden_size = int(hidden_size)
        self.num_quantiles = max(1, int(num_quantiles))

        taus = (torch.arange(self.num_quantiles, dtype=torch.float32) + 0.5) / float(self.num_quantiles)
        self.register_buffer("quantile_taus", taus)

        tcn_out_dim = int(tcn_channels[-1])
        self.tcn = TemporalConvNet(
            num_inputs=self.n_observations,
            num_channels=tcn_channels,
            kernel_size=kernel_size,
            dropout=dropout,
        )
        self.temporal_pool = TemporalAttentionPool(tcn_out_dim, dropout=dropout)

        fusion_input_dim = tcn_out_dim + self.pae_latent_dim
        fusion_fc = nn.Linear(fusion_input_dim, self.hidden_size)
        init_orthogonal(fusion_fc, gain=1.41421356)
        self.fusion_layer = nn.Sequential(
            fusion_fc,
            nn.LayerNorm(self.hidden_size),
            nn.SiLU(),
            nn.Dropout(dropout),
        )

        # Distributional Dueling Streams: [B, n_actions * N_quantiles] and [B, 1 * N_quantiles]
        adv_fc1 = nn.Linear(self.hidden_size, self.hidden_size)
        adv_fc2 = nn.Linear(self.hidden_size, self.n_actions * self.num_quantiles)
        val_fc1 = nn.Linear(self.hidden_size, self.hidden_size)
        val_fc2 = nn.Linear(self.hidden_size, self.num_quantiles)
        init_orthogonal(adv_fc1, gain=1.41421356)
        init_orthogonal(adv_fc2, gain=0.1)
        init_orthogonal(val_fc1, gain=1.41421356)
        init_orthogonal(val_fc2, gain=1.0)

        self.advantage_stream = nn.Sequential(adv_fc1, nn.SiLU(), adv_fc2)
        self.value_stream = nn.Sequential(val_fc1, nn.SiLU(), val_fc2)

    def _extract_fused_features(
        self, state_sequence: torch.Tensor, pae_latent: Optional[torch.Tensor]
    ) -> torch.Tensor:
        if hasattr(state_sequence, "dim") and state_sequence.dim() == 2:
            state_sequence = state_sequence.unsqueeze(1)

        x = state_sequence.transpose(1, 2)
        x = align_tcn_input_channels(x, self.tcn)

        temporal_out = self.tcn(x)
        temporal_features = self.temporal_pool(temporal_out)

        if self.pae_latent_dim <= 0:
            return self.fusion_layer(temporal_features)

        if pae_latent is None:
            pae_latent = torch.zeros(
                temporal_features.size(0),
                self.pae_latent_dim,
                device=getattr(temporal_features, "device", "cpu"),
            )

        if (
            hasattr(pae_latent, "device")
            and hasattr(temporal_features, "device")
            and pae_latent.device != temporal_features.device
        ):
            pae_latent = pae_latent.to(temporal_features.device)

        if hasattr(pae_latent, "shape") and len(pae_latent.shape) > 1 and isinstance(pae_latent.shape[1], int):
            if pae_latent.shape[1] < self.pae_latent_dim:
                pad_size = self.pae_latent_dim - pae_latent.shape[1]
                pae_latent = F.pad(pae_latent, (0, pad_size))
            elif pae_latent.shape[1] > self.pae_latent_dim:
                pae_latent = pae_latent[:, : self.pae_latent_dim]

        fused = torch.cat([temporal_features, pae_latent], dim=-1)
        return self.fusion_layer(fused)

    def forward_quantiles(
        self, state_sequence: torch.Tensor, pae_latent: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """
        Computes distributional action-value quantiles `[batch_size, n_actions, num_quantiles]`.
        """
        fused = self._extract_fused_features(state_sequence, pae_latent)
        batch_size = fused.size(0) if hasattr(fused, "size") else -1

        adv_q = self.advantage_stream(fused).view(batch_size, self.n_actions, self.num_quantiles)
        val_q = self.value_stream(fused).view(batch_size, 1, self.num_quantiles)

        return val_q + (adv_q - adv_q.mean(dim=1, keepdim=True))

    def forward(
        self, state_sequence: torch.Tensor, pae_latent: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """
        Computes expected Q-values `[batch_size, n_actions]` by averaging across quantiles.
        """
        q_quantiles = self.forward_quantiles(state_sequence, pae_latent)
        return q_quantiles.mean(dim=-1)
