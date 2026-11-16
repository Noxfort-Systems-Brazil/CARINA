# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Universal PAE latent state augmentation and ST-GATv2 strategic context fusion."""

from typing import Any, Optional

import torch
import torch.nn as nn
import torch.nn.functional as F


class PAEStateAugmentor:
    """
    Handles Universal PAE latent projection, optional ST-GATv2 strategic context fusion,
    and temporal sequence state augmentation without breaking agent channel dimensions.
    """

    def __init__(self, shared_pae: Optional[Any] = None) -> None:
        self.shared_pae = shared_pae
        self.latent_dim = shared_pae.latent_dim if shared_pae else 0

    @staticmethod
    def _align_context_to_dim(vec: torch.Tensor, target_dim: int) -> torch.Tensor:
        """Projects/pads/pools a `[batch, gat_dim]` strategic vector onto `[batch, target_dim]`."""
        cur_dim = vec.size(-1)
        if cur_dim == target_dim:
            return vec
        if cur_dim < target_dim:
            return F.pad(vec, (0, target_dim - cur_dim))
        return F.adaptive_avg_pool1d(vec.unsqueeze(1), target_dim).squeeze(1)

    @staticmethod
    def _align_to_reference(tensor: Any, reference: torch.Tensor) -> Any:
        if not hasattr(tensor, "to"):
            return tensor
        if hasattr(reference, "device") and hasattr(tensor, "device") and tensor.device != reference.device:
            tensor = tensor.to(reference.device)
        if hasattr(reference, "dtype") and hasattr(tensor, "dtype") and tensor.dtype != reference.dtype:
            tensor = tensor.to(dtype=reference.dtype)
        return tensor

    def _fuse_strategic_context(self, latent: torch.Tensor, strategic_context: Optional[torch.Tensor]) -> torch.Tensor:
        """Applies residual Green-Wave strategic fusion (ST-GATv2 -> latent context)."""
        if (
            strategic_context is None
            or not isinstance(getattr(nn, "Linear", None), type)
            or not isinstance(latent, torch.Tensor)
            or latent.size(-1) <= 0
        ):
            return latent

        strat = strategic_context
        if hasattr(strat, "dim") and strat.dim() == 1:
            strat = strat.unsqueeze(0)
        if strat.device != latent.device or strat.dtype != latent.dtype:
            strat = strat.to(device=latent.device, dtype=latent.dtype)
        if strat.size(0) == 1 and latent.size(0) > 1:
            strat = strat.expand(latent.size(0), -1)
        strat_aligned = self._align_context_to_dim(strat, latent.size(-1))
        return latent + 0.25 * torch.tanh(strat_aligned)

    def augment(
        self,
        state_tensor: torch.Tensor,
        precomputed_latent: Optional[torch.Tensor] = None,
        strategic_context: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        if self.shared_pae is None and precomputed_latent is None:
            return state_tensor

        with torch.no_grad():
            if precomputed_latent is not None:
                latent = precomputed_latent
                if hasattr(latent, "dim") and latent.dim() == 1:
                    latent = latent.unsqueeze(0)
            elif self.shared_pae is not None:
                latent = self.shared_pae.encode(state_tensor)  # [batch, latent_dim]
            else:
                return state_tensor

            latent = self._align_to_reference(latent, state_tensor)
            latent = self._fuse_strategic_context(latent, strategic_context)
            latent_expanded = latent.unsqueeze(1).expand(-1, state_tensor.size(1), -1)  # [batch, seq_len, latent_dim]
            return torch.cat([state_tensor, latent_expanded], dim=-1)
