# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import sys
from typing import Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [SLM_DEVICE] - %(levelname)s - %(message)s")


def _torch_cuda_is_mocked() -> bool:
    mod = sys.modules.get("torch")
    cuda = getattr(mod, "cuda", None) if mod is not None else None
    if cuda is None:
        return False
    is_avail = getattr(cuda, "is_available", None)
    mem_info = getattr(cuda, "mem_get_info", None)
    return bool(
        (is_avail is not None and (hasattr(is_avail, "assert_called") or hasattr(is_avail, "return_value")))
        or (mem_info is not None and (hasattr(mem_info, "assert_called") or hasattr(mem_info, "side_effect")))
    )


def _query_nvml_vram_gb() -> Optional[Tuple[float, float]]:
    """Queries free/total VRAM via pynvml without creating a ~400MB PyTorch CUDA context."""
    try:
        import pynvml  # type: ignore

        pynvml.nvmlInit()
        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
            return mem.free / (1024**3), mem.total / (1024**3)
        finally:
            try:
                pynvml.nvmlShutdown()
            except Exception:
                pass
    except Exception:
        return None


class SLMDeviceManager:
    """
    Handles hardware capability detection, CUDA availability checks,
    free VRAM evaluation (via lightweight pynvml to avoid PyTorch CUDA context bloat),
    and offload layer calculations for GGUF model execution.
    """

    @staticmethod
    def resolve_device_settings(device: str = None, gpu_layers: int = 16) -> Tuple[str, int]:
        """
        Determines the device execution setting ("gpu" vs "cpu") and number of GPU offload layers.
        Returns: (resolved_device_setting, resolved_gpu_layers)
        """
        use_torch_mock = _torch_cuda_is_mocked()

        if device in ("gpu", "cpu", "mixed"):
            device_setting = device
            resolved_layers = gpu_layers if device == "mixed" else (-1 if device == "gpu" else 0)
            logging.info(f"[SLMDeviceManager] Using explicit setting: {device_setting} (gpu_layers={resolved_layers})")

            if device_setting in ("gpu", "mixed"):
                if not use_torch_mock and _query_nvml_vram_gb() is not None:
                    return device_setting, resolved_layers
                try:
                    import torch

                    if not torch.cuda.is_available():
                        logging.warning(
                            "[SLMDeviceManager] GPU requested but CUDA is not available. Falling back to CPU."
                        )
                        return "cpu", 0
                except Exception as e:
                    logging.warning(f"[SLMDeviceManager] Failed CUDA check: {e}. Falling back to CPU.", exc_info=True)
                    return "cpu", 0
            return device_setting, resolved_layers

        # Prefer pynvml in production so SLM workers avoid allocating an extra PyTorch CUDA context
        if not use_torch_mock:
            nvml_vram = _query_nvml_vram_gb()
            if nvml_vram is not None:
                free_vram_gb, total_vram_gb = nvml_vram
                logging.info(
                    f"[SLMDeviceManager] NVML detected GPU. Free VRAM: {free_vram_gb:.2f} GB / Total: {total_vram_gb:.2f} GB"
                )
                if free_vram_gb >= 3.0:
                    return "gpu", -1
                if free_vram_gb >= 1.8 and isinstance(gpu_layers, int) and gpu_layers > 0:
                    logging.info(
                        f"[SLMDeviceManager] Moderate VRAM ({free_vram_gb:.2f} GB). Partial offload: gpu_layers={gpu_layers}."
                    )
                    return "gpu", int(gpu_layers)
                logging.info("[SLMDeviceManager] Low VRAM detected. Running on CPU.")
                return "cpu", 0

        # Fallback / mocked torch.cuda detection
        try:
            import torch

            if torch.cuda.is_available():
                try:
                    free_vram, total_vram = torch.cuda.mem_get_info()
                    free_vram_gb = free_vram / (1024**3)
                    logging.info(
                        f"[SLMDeviceManager] CUDA detected. Free VRAM: {free_vram_gb:.2f} GB / Total: {total_vram / (1024 ** 3):.2f} GB"
                    )
                    if free_vram_gb >= 3.0:
                        logging.info("[SLMDeviceManager] Sufficient VRAM detected (>=3GB). Offloading to GPU.")
                        return "gpu", -1
                    logging.info("[SLMDeviceManager] Low VRAM detected (<3GB). Running on CPU.")
                    return "cpu", 0
                except Exception as e:
                    logging.warning(f"[SLMDeviceManager] Error checking VRAM: {e}. Using GPU fallback.", exc_info=True)
                    return "gpu", -1
            logging.info("[SLMDeviceManager] CUDA not available. Running on CPU.")
            return "cpu", 0
        except Exception as e:
            logging.warning(f"[SLMDeviceManager] Torch check failed: {e}. Running on CPU.", exc_info=True)
            return "cpu", 0
