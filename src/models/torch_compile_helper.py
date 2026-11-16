# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""PyTorch 2.0+ `torch.compile` warmup and safe eager-mode fallback helper for PAE."""

import logging
from typing import Any

import torch


def compile_pae_submodules(
    pae_module: Any,
    enable_compile: bool = True,
    mode: str = "reduce-overhead",
    warmup_batch_size: int = 1,
) -> None:
    """Applies `torch.compile` with synthetic warmup to PAE submodules and falls back safely to eager mode."""
    if not enable_compile:
        return
    if not hasattr(torch, "compile"):
        logging.info("[PAE] torch.compile not available in this PyTorch version. Keeping eager mode.")
        return

    try:
        logging.info(f"[PAE] Compiling iTransformer modules with mode='{mode}'...")
        compiled_encoder = torch.compile(pae_module.transformer_encoder, mode=mode)
        compiled_latent_proj = torch.compile(pae_module.latent_proj, mode=mode)
        compiled_decoder = torch.compile(pae_module.decoder, mode=mode)

        dev = pae_module.device
        dummy = torch.randn(warmup_batch_size, pae_module.input_dim, pae_module.d_model, device=dev)
        dummy_pool = torch.randn(warmup_batch_size, pae_module.num_latent_queries * pae_module.d_model, device=dev)
        with torch.no_grad():
            _ = compiled_encoder(dummy)
            z = compiled_latent_proj(dummy_pool)
            _ = compiled_decoder(z)

        pae_module.transformer_encoder = compiled_encoder
        pae_module.latent_proj = compiled_latent_proj
        pae_module.decoder = compiled_decoder
        logging.info(f"[PAE] Compilation successful with warmup (batch_size={warmup_batch_size}).")
    except Exception as e:
        logging.warning(f"[PAE] torch.compile fallback to eager mode: {e}", exc_info=True)
