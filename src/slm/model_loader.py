# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import os
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [SLM_LOADER] - %(levelname)s - %(message)s")


class SLMModelLoader:
    """
    Encapsulates loading and initialization of GGUF model files using llama-cpp-python,
    handling GPU acceleration and automatic CPU fallback.
    """

    @staticmethod
    def load_model(model_path: str, device_setting: str, gpu_layers: int) -> Any:
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
                model = Llama(model_path=model_path, n_ctx=8192, n_gpu_layers=n_gpu_layers, verbose=False)
                logging.info("[SLMModelLoader] GGUF model loaded successfully on GPU.")
                return model
            except Exception as e:
                logging.warning(
                    f"[SLMModelLoader] GPU load failed (gpu_layers={n_gpu_layers}): {e}. Attempting CPU fallback..."
                , exc_info=True)

        if model is None:
            try:
                logging.info(f"[SLMModelLoader] Loading GGUF model on CPU (gpu_layers=0): {model_path}")
                model = Llama(model_path=model_path, n_ctx=8192, n_gpu_layers=0, verbose=False)
                logging.info("[SLMModelLoader] GGUF model loaded successfully on CPU.")
                return model
            except ImportError:
                raise RuntimeError("llama-cpp-python is not installed. Please install it to use GGUF models.")
            except Exception as e:
                logging.error(f"[SLMModelLoader] CPU model loading failed: {e}", exc_info=True)
                raise RuntimeError(f"Failed to load model resources: {e}")
