# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import os
from typing import Any, Optional


class HardwareInitializer:
    """
    Utility component responsible for configuring Deep Learning hardware settings,
    PyTorch CPU thread bounds, PyInstaller PyTorch JIT compatibility shims,
    and CUDA GPU acceleration parameters.
    """

    @staticmethod
    def setup_environment(logging_func: Optional[Any] = None) -> None:
        """
        Configures CPU thread limits, PyTorch JIT shims for frozen builds,
        and TensorCore (TF32) precision settings.

        Args:
            logging_func (Optional[Any]): Optional logger callback function.
        """
        import torch

        # Bound CPU threads to prevent CPU contention during multi-process execution
        os.environ["OMP_NUM_THREADS"] = "1"
        os.environ["MKL_NUM_THREADS"] = "1"
        os.environ["OPENBLAS_NUM_THREADS"] = "1"
        if hasattr(torch, "set_num_threads"):
            torch.set_num_threads(1)

        # PyInstaller + TorchScript compatibility shim for frozen builds
        def _jit_script_shim(obj, *args, **kwargs):
            return obj

        if hasattr(torch, "jit"):
            torch.jit.script = _jit_script_shim

        # Hardware Acceleration: TensorCore (TF32/FP16) & cuDNN benchmark optimization
        if hasattr(torch, "backends") and hasattr(torch.backends, "cuda"):
            torch.backends.cuda.matmul.allow_tf32 = True
            if hasattr(torch.backends, "cudnn"):
                torch.backends.cudnn.allow_tf32 = True
                torch.backends.cudnn.benchmark = True
        if hasattr(torch, "set_float32_matmul_precision"):
            torch.set_float32_matmul_precision("high")

        log_msg = "⚡ Hardware Acceleration (TensorCores/TF32) enabled strictly (CPU Threads bounded to 1)."
        if logging_func:
            logging_func(log_msg, level="info")
        else:
            logging.info(log_msg)

    @staticmethod
    def detect_gpu(locale_manager: Optional[Any] = None, logging_func: Optional[Any] = None) -> str:
        """
        Detects CUDA GPU availability and returns device metadata string.

        Args:
            locale_manager (Optional[Any]): Optional LocaleManagerBackend instance for i18n logging.
            logging_func (Optional[Any]): Optional logger callback function.

        Returns:
            str: GPU device name or 'N/A' if GPU is unavailable.
        """
        import torch

        gpu_info = "N/A"
        if hasattr(torch, "cuda") and torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            gpu_info = gpu_name
            msg = (
                locale_manager.get_string(
                    "main_ai.gpu_detected", default="✅ GPU Detected: {gpu_name}", gpu_name=gpu_name
                )
                if locale_manager and hasattr(locale_manager, "get_string")
                else f"✅ GPU Detected: {gpu_name}"
            )
            if logging_func:
                logging_func(msg, level="info")
            else:
                logging.info(msg)
        else:
            msg = (
                locale_manager.get_string("main_ai.no_gpu", default="⚠️ No GPU detected. Running on CPU.")
                if locale_manager and hasattr(locale_manager, "get_string")
                else "⚠️ No GPU detected. Running on CPU."
            )
            if logging_func:
                logging_func(msg, level="warning")
            else:
                logging.warning(msg)

        return gpu_info
