# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Batched Universal PAE latent extraction across active fleet intersections."""

import logging
import sys
from typing import Any, Dict, List

import torch

try:
    from models.pae import PredictiveAutoencoder as _RelPAE
except ImportError:
    _RelPAE = None

try:
    from src.models.pae import PredictiveAutoencoder as _SrcPAE
except ImportError:
    _SrcPAE = None


def _is_predictive_autoencoder(candidate: Any) -> bool:
    """Recognizes PredictiveAutoencoder regardless of `models.*` vs `src.models.*` import path."""
    if candidate is None:
        return False
    classes = [cls for cls in (_RelPAE, _SrcPAE) if isinstance(cls, type)]
    for mod_name in ("models.pae", "src.models.pae"):
        mod = sys.modules.get(mod_name)
        cls = getattr(mod, "PredictiveAutoencoder", None) if mod is not None else None
        if isinstance(cls, type) and cls not in classes:
            classes.append(cls)
    return bool(classes) and isinstance(candidate, tuple(classes))


class BatchedPAEEncoder:
    """Encodes heterogeneous intersection state sequences in a single batched PAE forward pass."""

    @staticmethod
    def _find_shared_pae(agents: Dict[str, Any]) -> Any:
        for agent in agents.values():
            shared_pae = getattr(agent, "shared_pae", None)
            if shared_pae is not None:
                return shared_pae
        return None

    def encode_fleet(
        self,
        agents: Dict[str, Any],
        precomputed_states: Dict[str, Any],
    ) -> Dict[str, torch.Tensor]:
        shared_pae = self._find_shared_pae(agents)
        precomputed_latents: Dict[str, torch.Tensor] = {}
        if shared_pae is None or not precomputed_states:
            return precomputed_latents

        try:
            valid_tls = [tl for tl in agents.keys() if tl in precomputed_states]
            if not valid_tls:
                return precomputed_latents

            is_real_pae = _is_predictive_autoencoder(shared_pae)
            tensors_to_batch: List[torch.Tensor] = []
            orig_dims: List[int] = []
            for tl in valid_tls:
                t = precomputed_states[tl][1]
                if is_real_pae and hasattr(t, "shape") and len(t.shape) >= 1:
                    orig_dims.append(int(t.shape[-1]))
                if hasattr(shared_pae, "standardize_sequence"):
                    t = shared_pae.standardize_sequence(t)
                if is_real_pae and hasattr(shared_pae, "pad_to_input_dim"):
                    t = shared_pae.pad_to_input_dim(t)
                tensors_to_batch.append(t)

            batch_tensor = torch.cat(tensors_to_batch, dim=0)
            device_type = (
                shared_pae.device.type
                if hasattr(shared_pae, "device") and hasattr(shared_pae.device, "type")
                else "cpu"
            )
            with torch.no_grad(), torch.amp.autocast(device_type=device_type, enabled=(device_type == "cuda")):
                if is_real_pae and orig_dims:
                    valid_dims_t = torch.tensor(orig_dims, dtype=torch.long, device=batch_tensor.device)
                    all_latents = shared_pae.encode(batch_tensor, valid_dims=valid_dims_t)
                else:
                    all_latents = shared_pae.encode(batch_tensor)

            for idx, tl in enumerate(valid_tls):
                precomputed_latents[tl] = all_latents[idx : idx + 1]
        except Exception as e:
            logging.debug(f"[AgentEvaluator] Batched PAE encoding fallback: {e}")

        return precomputed_latents
