# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Predictive Autoencoder (PAE) Universal — Action-Conditioned World Model (iTransformer Backbone).

Shared by reference across all LocalAgents, GuardianAgents, and the StrategicCoordinator:
- Per-Variable RevIN (Reversible Instance Normalization) + explicit scale statistics
  embedding (`[mean, std]`) to decouple temporal dynamics from static saturation scale.
- Cross-Attention Latent Pooling with Key Padding Mask (`valid_dims`) so intersections
  with fewer lanes/edges never contaminate the latent space with zero-padded tokens.
- Binary Action Conditioning (`0 = ADVANCE`, `1 = KEEP`) and Heteroscedastic Uncertainty
  head (`decode_with_uncertainty -> (mean, log_var)`) for counterfactual world modeling.
"""

import logging
from typing import Any, Optional, Tuple, Union

import torch
import torch.nn as nn

from src.models.pae_preprocessing import build_key_padding_mask, pad_to_input_dim, standardize_sequence
from src.models.tcn_backbone import init_orthogonal
from src.models.torch_compile_helper import compile_pae_submodules


class PredictiveAutoencoder(nn.Module):
    """
    Universal Action-Conditioned iTransformer World Model for urban fluid dynamics.
    Pure Neural Network architecture (Domain Entity), initialized in `.eval()` mode.
    """

    def __init__(
        self,
        input_dim: int,
        latent_dim: int = 16,
        history_len: int = 16,
        d_model: int = 32,
        nhead: int = 4,
        num_layers: int = 2,
        dropout: float = 0.1,
        lr: Optional[float] = None,
        n_actions: int = 2,
        num_latent_queries: int = 4,
        **kwargs: Any,
    ) -> None:
        super().__init__()

        self.input_dim = int(input_dim)
        self.latent_dim = int(latent_dim)
        self.history_len = int(history_len)
        self.d_model = int(d_model)
        self.n_actions = int(n_actions)
        self.num_latent_queries = int(num_latent_queries)

        # Ensure nhead divides d_model cleanly
        effective_nhead = int(nhead)
        while effective_nhead > 1 and (self.d_model % effective_nhead != 0):
            effective_nhead -= 1
        self.nhead = effective_nhead

        # 1. Per-variable RevIN affine parameters + scale statistics embedding ([mean, std] -> d_model)
        self.revin_gamma = nn.Parameter(torch.ones(1, 1, self.input_dim))
        self.revin_beta = nn.Parameter(torch.zeros(1, 1, self.input_dim))
        self.stats_proj = nn.Linear(2, self.d_model)
        init_orthogonal(self.stats_proj, gain=0.5)

        # 2. Temporal projection per variable: [history_len] -> [d_model]
        self.value_embedding = nn.Linear(self.history_len, self.d_model)
        init_orthogonal(self.value_embedding, gain=1.0)

        # 3. Variable/Channel positional embedding
        self.var_embedding = nn.Parameter(torch.randn(1, self.input_dim, self.d_model) * 0.02)

        # 4. Inverted Transformer Encoder over variable tokens
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=self.d_model,
            nhead=self.nhead,
            dim_feedforward=self.d_model * 4,
            dropout=dropout,
            activation="gelu",
            layer_norm_eps=1e-5,
            batch_first=True,
        )
        self.transformer_encoder = nn.TransformerEncoder(
            encoder_layer, num_layers=num_layers, enable_nested_tensor=False
        )

        # 5. Cross-Attention Latent Pooling with learnable query tokens (ignores zero-padded channels)
        self.latent_queries = nn.Parameter(torch.randn(1, self.num_latent_queries, self.d_model) * 0.02)
        self.cross_attn_pool = nn.MultiheadAttention(
            embed_dim=self.d_model, num_heads=self.nhead, dropout=dropout, batch_first=True
        )
        self.pool_norm = nn.LayerNorm(self.d_model)

        self.latent_proj = nn.Sequential(
            nn.Linear(self.num_latent_queries * self.d_model, 64),
            nn.LayerNorm(64),
            nn.SiLU(),
            nn.Linear(64, self.latent_dim),
        )

        # 6. Binary Action Conditioning (0 = ADVANCE, 1 = KEEP) + Probabilistic Next-State Decoder
        self.action_embedding = nn.Embedding(self.n_actions, self.latent_dim)
        if isinstance(getattr(self.action_embedding, "weight", None), torch.Tensor):
            nn.init.normal_(self.action_embedding.weight, mean=0.0, std=0.02)

        self.decoder = nn.Sequential(
            nn.Linear(self.latent_dim, 64),
            nn.LayerNorm(64),
            nn.SiLU(),
            nn.Linear(64, self.input_dim),
        )
        self.log_var_head = nn.Sequential(
            nn.Linear(self.latent_dim, 64),
            nn.LayerNorm(64),
            nn.SiLU(),
            nn.Linear(64, self.input_dim),
        )

        logging.info(
            f"[PAE] Action-Conditioned iTransformer World Model instantiated "
            f"(input={self.input_dim}, latent={self.latent_dim}, history={self.history_len}, "
            f"d_model={self.d_model}, n_actions={self.n_actions})"
        )
        self.eval()

    @property
    def device(self) -> torch.device:
        return next(self.parameters()).device

    def pad_to_input_dim(self, x: torch.Tensor) -> torch.Tensor:
        """Pads or truncates agent local state vectors to the universal PAE `input_dim`."""
        return pad_to_input_dim(x, self.input_dim)

    def standardize_sequence(self, x: torch.Tensor) -> torch.Tensor:
        """Standardizes 2D `[batch, dim]` or 3D `[batch, seq_len, dim]` inputs to `[batch, history_len, input_dim]`."""
        return standardize_sequence(x, self.input_dim, self.history_len)

    def _build_key_padding_mask(
        self, batch_size: int, orig_dim: int, valid_dims: Optional[torch.Tensor], device: Any
    ) -> Optional[torch.Tensor]:
        """Builds boolean mask `[batch_size, input_dim]` where `True` marks zero-padded channels."""
        return build_key_padding_mask(batch_size, orig_dim, self.input_dim, valid_dims, device)

    def encode(self, x: torch.Tensor, valid_dims: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Encodes `[batch_size, seq_len, dim]` or `[batch_size, dim]` into `[batch_size, latent_dim]`,
        applying per-variable RevIN and masking padded variable tokens.
        """
        if hasattr(x, "device") and hasattr(self, "device") and x.device != self.device:
            x = x.to(self.device)

        orig_dim = x.size(-1) if hasattr(x, "size") else self.input_dim
        x_std = self.standardize_sequence(x)  # [B, history_len, input_dim]
        batch_size = x_std.size(0)

        # 1. Per-variable RevIN across the temporal axis (dim=1)
        var_mean = x_std.mean(dim=1, keepdim=True)
        var_centered = x_std - var_mean
        var_std = torch.sqrt((var_centered * var_centered).mean(dim=1, keepdim=True) + 1e-5)
        x_norm = ((var_centered / var_std) * self.revin_gamma) + self.revin_beta

        # Invert dimensions: variables become tokens [B, input_dim, history_len]
        x_vars = x_norm.transpose(1, 2)

        # 2. Temporal shape embedding + absolute scale statistics ([mean, std]) + variable identity
        stats_pair = torch.cat([var_mean.transpose(1, 2), var_std.transpose(1, 2)], dim=-1)  # [B, input_dim, 2]
        x_emb = self.value_embedding(x_vars) + self.stats_proj(stats_pair) + self.var_embedding

        # 3. Masked Transformer self-attention over active variables
        padding_mask = self._build_key_padding_mask(
            batch_size=batch_size, orig_dim=orig_dim, valid_dims=valid_dims, device=getattr(x_std, "device", "cpu")
        )
        if padding_mask is not None:
            x_out = self.transformer_encoder(x_emb, src_key_padding_mask=padding_mask)
        else:
            x_out = self.transformer_encoder(x_emb)

        # 4. Cross-Attention Latent Pooling using learnable queries
        queries = self.latent_queries.expand(batch_size, -1, -1)
        if padding_mask is not None:
            attn_res = self.cross_attn_pool(queries, x_out, x_out, key_padding_mask=padding_mask, need_weights=False)
        else:
            attn_res = self.cross_attn_pool(queries, x_out, x_out, need_weights=False)

        pooled = attn_res[0] if isinstance(attn_res, tuple) else attn_res
        pooled = self.pool_norm(pooled + queries)
        flat = pooled.reshape(batch_size, -1)
        return self.latent_proj(flat)

    def _condition_latent(self, z: torch.Tensor, action: Optional[Union[int, torch.Tensor]] = None) -> torch.Tensor:
        """Injects binary action embedding (`0=ADVANCE`, `1=KEEP`) into the latent representation."""
        if action is None:
            return z
        if not isinstance(getattr(nn, "Linear", None), type):
            return z

        batch_size = z.size(0)
        if isinstance(action, int):
            act_tensor = torch.full((batch_size,), action, dtype=torch.long, device=z.device)
        elif isinstance(action, torch.Tensor):
            act_tensor = action.to(device=z.device, dtype=torch.long).view(-1)
            if act_tensor.numel() == 1 and batch_size > 1:
                act_tensor = act_tensor.expand(batch_size)
        else:
            act_tensor = torch.as_tensor(action, dtype=torch.long, device=z.device).view(-1)
            if act_tensor.numel() == 1 and batch_size > 1:
                act_tensor = act_tensor.expand(batch_size)

        act_tensor = torch.clamp(act_tensor, min=0, max=self.n_actions - 1)
        return z + self.action_embedding(act_tensor)

    def decode(self, z: torch.Tensor, action: Optional[Union[int, torch.Tensor]] = None) -> torch.Tensor:
        """
        Predicts the next state mean `[batch_size, input_dim]` from `z` (optionally conditioned on `action`).
        """
        if hasattr(z, "device") and hasattr(self, "device") and z.device != self.device:
            z = z.to(self.device)
        z_cond = self._condition_latent(z, action=action)
        return self.decoder(z_cond)

    def decode_with_uncertainty(
        self, z: torch.Tensor, action: Optional[Union[int, torch.Tensor]] = None
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Predicts `(next_state_mean, next_state_log_var)` for heteroscedastic uncertainty estimation
        and counterfactual spillback risk assessment.
        """
        if hasattr(z, "device") and hasattr(self, "device") and z.device != self.device:
            z = z.to(self.device)
        z_cond = self._condition_latent(z, action=action)
        mean = self.decoder(z_cond)
        log_var = torch.clamp(self.log_var_head(z_cond), -6.0, 2.0)
        return mean, log_var

    def forward(
        self,
        x: torch.Tensor,
        action: Optional[Union[int, torch.Tensor]] = None,
        valid_dims: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        Full world-model pass: `encode(x, valid_dims) -> decode(z, action)`.
        """
        z = self.encode(x, valid_dims=valid_dims)
        return self.decode(z, action=action)

    def optimize_engine(
        self, enable_compile: bool = True, mode: str = "reduce-overhead", warmup_batch_size: int = 1
    ) -> None:
        """Applies PyTorch 2.0+ `torch.compile` with synthetic warmup and safe eager fallback."""
        compile_pae_submodules(self, enable_compile=enable_compile, mode=mode, warmup_batch_size=warmup_batch_size)
