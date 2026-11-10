# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional

import torch
import torch.nn as nn

from models.pae import PredictiveAutoencoder


class CaptumModelWrapper(nn.Module):
    """
    Wrapper that encapsulates the agent's model for Captum compatibility.
    Applies differentiable PAE latent augmentation end-to-end (preserving gradient
    flow through PredictiveAutoencoder) and outputs raw uncalibrated logits to
    avoid post-softmax gradient saturation during Integrated Gradients.
    """

    def __init__(self, model: nn.Module, shared_pae: Optional[PredictiveAutoencoder] = None) -> None:
        super(CaptumModelWrapper, self).__init__()
        self.model = model
        self.shared_pae = shared_pae
        if hasattr(self.model, "eval"):
            self.model.eval()
        if self.shared_pae is not None and hasattr(self.shared_pae, "eval"):
            self.shared_pae.eval()

    def _get_expected_dim(self) -> Optional[int]:
        try:
            in_ch = self.model.tcn.network[0].conv1.in_channels
            return int(in_ch) if isinstance(in_ch, int) else None
        except Exception:
            return None

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if self.shared_pae is not None:
            if isinstance(self.shared_pae, PredictiveAutoencoder):
                orig_dim = int(x.shape[-1]) if hasattr(x, "shape") and len(x.shape) >= 1 else self.shared_pae.input_dim
                pae_seq = self.shared_pae.standardize_sequence(x)
                pae_seq = self.shared_pae.pad_to_input_dim(pae_seq)
                valid_dims = torch.full(
                    (x.shape[0],),
                    min(orig_dim, self.shared_pae.input_dim),
                    dtype=torch.long,
                    device=x.device,
                )
                latent = self.shared_pae.encode(pae_seq, valid_dims=valid_dims)
            else:
                original_dim = self.shared_pae.input_dim
                original_seq = x[:, :, :original_dim]
                latent = self.shared_pae.encode(original_seq)

            if (
                hasattr(latent, "to")
                and hasattr(x, "device")
                and hasattr(latent, "device")
                and latent.device != x.device
            ):
                latent = latent.to(x.device)
            latent_expanded = latent.unsqueeze(1).expand(-1, x.size(1), -1)
            x = torch.cat([x, latent_expanded], dim=-1)

        expected_dim = self._get_expected_dim()
        if (
            expected_dim is not None
            and hasattr(x, "shape")
            and len(x.shape) >= 1
            and isinstance(x.shape[-1], int)
            and x.shape[-1] < expected_dim
        ):
            padding_dim = expected_dim - x.shape[-1]
            zeros = torch.zeros(*x.shape[:-1], padding_dim, device=x.device, dtype=x.dtype)
            x = torch.cat([x, zeros], dim=-1)

        if getattr(self.model, "outputs_logits", None) is True and hasattr(self.model, "forward_logits"):
            logits, _ = self.model.forward_logits(x)
            return logits

        return self.model(x)[0]

    def to(self, *args, **kwargs) -> "CaptumModelWrapper":
        # Call parent's to if it exists (real PyTorch nn.Module)
        if hasattr(super(CaptumModelWrapper, self), "to"):
            super(CaptumModelWrapper, self).to(*args, **kwargs)
        return self

    def __call__(self, *args, **kwargs) -> torch.Tensor:
        return self.forward(*args, **kwargs)
