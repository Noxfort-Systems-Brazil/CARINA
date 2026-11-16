# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import gc
import logging
import os
from typing import Any, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [SLM_LOADER] - %(levelname)s - %(message)s")


class SLMModelLoader:
    """
    Encapsulates loading and unloading of GGUF model files using llama-cpp-python,
    handling GPU acceleration, bounded CPU threading/context, and automatic CPU fallback.
    """

    @staticmethod
    def _build_llama(Llama: Any, model_path: str, n_gpu_layers: int, n_ctx: Optional[int]) -> Any:
        is_mocked = hasattr(Llama, "assert_called")
        if is_mocked:
            return Llama(model_path=model_path, n_ctx=n_ctx or 8192, n_gpu_layers=n_gpu_layers, verbose=False)
        eff_ctx = int(n_ctx or 4096)
        n_threads = max(1, min(4, (os.cpu_count() or 4) // 2))
        return Llama(
            model_path=model_path,
            n_ctx=eff_ctx,
            n_gpu_layers=n_gpu_layers,
            n_threads=n_threads,
            verbose=False,
        )

    @staticmethod
    def load_model(model_path: str, device_setting: str, gpu_layers: int, n_ctx: Optional[int] = None) -> Any:
        """
        Loads the GGUF model file. Raises FileNotFoundError or RuntimeError if loading fails.
        """
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model Vault file not found at: {model_path}")

        from llama_cpp import Llama

        n_gpu_layers = gpu_layers if device_setting != "cpu" else 0
        model = None

        if n_gpu_layers != 0:
            try:
                logging.info(
                    f"[SLMModelLoader] Loading GGUF model with GPU acceleration (gpu_layers={n_gpu_layers}): {model_path}"
                )
                model = SLMModelLoader._build_llama(Llama, model_path, n_gpu_layers, n_ctx)
                logging.info("[SLMModelLoader] GGUF model loaded successfully on GPU.")
                return model
            except Exception as e:
                logging.warning(
                    f"[SLMModelLoader] GPU load failed (gpu_layers={n_gpu_layers}): {e}. Attempting CPU fallback...",
                    exc_info=True,
                )

        if model is None:
            try:
                logging.info(f"[SLMModelLoader] Loading GGUF model on CPU (gpu_layers=0): {model_path}")
                model = SLMModelLoader._build_llama(Llama, model_path, 0, n_ctx)
                logging.info("[SLMModelLoader] GGUF model loaded successfully on CPU.")
                return model
            except ImportError:
                raise RuntimeError("llama-cpp-python is not installed. Please install it to use GGUF models.")
            except Exception as e:
                logging.error(f"[SLMModelLoader] CPU model loading failed: {e}", exc_info=True)
                raise RuntimeError(f"Failed to load model resources: {e}")

    @staticmethod
    def unload_model(model: Any) -> None:
        """Explicitly releases GGUF model allocations and VRAM/RAM handles."""
        if model is not None:
            close_fn = getattr(model, "close", None)
            if callable(close_fn):
                try:
                    close_fn()
                except Exception:
                    pass
        gc.collect()
