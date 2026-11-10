# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional, Tuple, Union

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GATv2Conv

from src.models.tcn_backbone import Chomp1d, TemporalAttentionPool, TemporalConv1d, init_orthogonal


class TemporalConvNetLite(nn.Module):
    """
    Lightweight Causal Dilated 1D Temporal Convolutional Network.
    Processes `[N, input_dim, T]` with causal channel-wise `GroupNorm(1, C)` and `SiLU`
    to extract platoon progression, queue gradients, and phase dynamics.
    """

    def __init__(self, in_channels: int, out_channels: int, kernel_size: int = 3, dropout: float = 0.1) -> None:
        super().__init__()
        dilation1 = 1
        pad1 = (kernel_size - 1) * dilation1
        self.conv1 = TemporalConv1d(in_channels, out_channels, kernel_size, padding=pad1, dilation=dilation1)
        self.chomp1 = Chomp1d(pad1)
        self.norm1 = nn.GroupNorm(1, out_channels)
        self.act1 = nn.SiLU()
        self.dropout1 = nn.Dropout(dropout)

        dilation2 = 2
        pad2 = (kernel_size - 1) * dilation2
        self.conv2 = TemporalConv1d(out_channels, out_channels, kernel_size, padding=pad2, dilation=dilation2)
        self.chomp2 = Chomp1d(pad2)
        self.norm2 = nn.GroupNorm(1, out_channels)
        self.act2 = nn.SiLU()
        self.dropout2 = nn.Dropout(dropout)

        self.residual = nn.Conv1d(in_channels, out_channels, 1) if in_channels != out_channels else None
        if self.residual is not None:
            init_orthogonal(self.residual, gain=1.0)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: [N, in_channels, T]
        res = x if self.residual is None else self.residual(x)
        out = self.dropout1(self.act1(self.norm1(self.chomp1(self.conv1(x)))))
        out = self.dropout2(self.act2(self.norm2(self.chomp2(self.conv2(out)))))
        return out + res


class STGATv2Lite(nn.Module):
    """
    Spatiotemporal Graph Attention Network v2 (`ST-GATv2 Lite`) for arterial Green-Wave coordination:
    - Causal TCN + `TemporalAttentionPool` over rolling intersection state sequences.
    - Multi-head `GATv2Conv` layers with physical `edge_attr` and spatial residual connections
      (`res_proj1`, `res_proj2`) to prevent graph over-smoothing.
    - Auxiliary `pred_head` for self-supervised future traffic forecasting AND `global_critic_head`
      for cooperative Centralized Training with Decentralized Execution (CTDE).
    """

    def __init__(
        self,
        input_dim: int,
        hidden_dim: int,
        output_dim: int,
        heads: int = 4,
        edge_dim: Optional[int] = 3,
        kernel_size: int = 3,
        pred_dim: Optional[int] = None,
    ) -> None:
        super().__init__()

        self.input_dim = int(input_dim)
        self.hidden_dim = int(hidden_dim)
        self.output_dim = int(output_dim)
        self.heads = int(heads)
        self.edge_dim = edge_dim
        self.pred_dim = int(pred_dim) if pred_dim is not None else self.input_dim

        # 1. Causal Dilated Temporal Feature Extractor + Temporal Attention Pool
        self.tcn = TemporalConvNetLite(
            in_channels=self.input_dim, out_channels=self.hidden_dim, kernel_size=kernel_size
        )
        self.temporal_pool = TemporalAttentionPool(self.hidden_dim, dropout=0.1)

        # 2. Spatial Attention Graph Convolution Layers + Residual Projections
        gat1_out = self.hidden_dim * self.heads
        self.conv1 = GATv2Conv(
            self.hidden_dim, self.hidden_dim, heads=self.heads, dropout=0.1, concat=True, edge_dim=edge_dim
        )
        self.res_proj1 = (
            nn.Linear(self.hidden_dim, gat1_out) if self.hidden_dim != gat1_out else nn.Identity()
        )
        self.norm1 = nn.LayerNorm(gat1_out)

        self.conv2 = GATv2Conv(
            gat1_out, self.output_dim, heads=1, dropout=0.1, concat=False, edge_dim=edge_dim
        )
        self.res_proj2 = nn.Linear(gat1_out, self.output_dim) if gat1_out != self.output_dim else nn.Identity()
        self.norm2 = nn.LayerNorm(self.output_dim)

        # 3. Auxiliary prediction head for self-supervised future forecasting (t + Delta)
        self.pred_head = nn.Sequential(
            nn.Linear(self.output_dim, self.hidden_dim),
            nn.SiLU(),
            nn.Linear(self.hidden_dim, self.pred_dim),
        )

        # 4. Cooperative Global Value Head for CTDE arterial reward alignment
        self.global_critic_head = nn.Sequential(
            nn.Linear(self.output_dim, self.hidden_dim),
            nn.SiLU(),
            nn.Linear(self.hidden_dim, 1),
        )

    def _align_node_features(self, x_seq: torch.Tensor) -> torch.Tensor:
        """Defensively pads or slices node feature dimension to `self.input_dim`."""
        try:
            feat_dim = x_seq.size(-1)
            if isinstance(feat_dim, int) and feat_dim != self.input_dim:
                if feat_dim < self.input_dim:
                    return F.pad(x_seq, (0, self.input_dim - feat_dim))
                return x_seq[..., : self.input_dim]
        except Exception:
            pass
        return x_seq

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_attr: Optional[torch.Tensor] = None,
        return_prediction: bool = False,
        return_value: bool = False,
    ) -> Union[torch.Tensor, Tuple[torch.Tensor, ...]]:
        """
        Spatiotemporal graph forward pass.
        """
        if x.dim() == 2:
            x_seq = x.unsqueeze(1)
        elif x.dim() == 3:
            x_seq = x
        else:
            raise ValueError(f"Expected x to be 2D [N, F] or 3D [N, T, F], but got shape {x.shape}")

        x_seq = self._align_node_features(x_seq)

        # Temporal convolution expects [num_nodes, channels, length]
        x_perm = x_seq.transpose(1, 2)
        h_temporal = self.tcn(x_perm)
        h_node = self.temporal_pool(h_temporal)

        # 1. GATv2 Layer 1 + Spatial Residual + LayerNorm
        if edge_attr is not None:
            h_gat1 = self.conv1(h_node, edge_index, edge_attr=edge_attr)
        else:
            h_gat1 = self.conv1(h_node, edge_index)
        h = self.norm1(F.elu(h_gat1) + self.res_proj1(h_node))
        h = F.dropout(h, p=0.1, training=getattr(self, "training", False))

        # 2. GATv2 Layer 2 + Spatial Residual + LayerNorm
        if edge_attr is not None:
            z_gat2 = self.conv2(h, edge_index, edge_attr=edge_attr)
        else:
            z_gat2 = self.conv2(h, edge_index)
        z = self.norm2(z_gat2 + self.res_proj2(h))

        if return_prediction and return_value:
            return z, self.pred_head(z), self.global_critic_head(z)
        if return_prediction:
            return z, self.pred_head(z)
        if return_value:
            return z, self.global_critic_head(z)
        return z

    def predict_future(self, z: torch.Tensor) -> torch.Tensor:
        """Projects strategic vectors `z` into predicted future state features."""
        return self.pred_head(z)

    def predict_global_value(self, z: torch.Tensor) -> torch.Tensor:
        """Projects node strategic embeddings `z` into cooperative CTDE value estimates `[N, 1]`."""
        return self.global_critic_head(z)


# Alias for backward compatibility
GATv2Lite = STGATv2Lite
