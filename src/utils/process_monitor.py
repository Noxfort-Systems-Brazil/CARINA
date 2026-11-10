# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import sys
import threading
import time
from typing import Optional

import psutil

from utils.metrics_manager import MetricsManager

try:
    import pynvml

    HAS_PYNVML = True
except ImportError:
    HAS_PYNVML = False


class ProcessMonitor:
    """
    Manages process resource utilization monitoring (CPU, memory, threads, GPU, VRAM)
    in a background daemon thread and registers metrics via MetricsManager.
    """

    @staticmethod
    def start_background_monitor(
        process_name: str = "AI_Process", port: int = 8002, interval: int = 5
    ) -> MetricsManager:
        """
        Initializes MetricsManager, registers system and hardware resource gauges,
        and starts a background daemon thread monitoring CPU, Memory, Threads,
        GPU utilization, and PyTorch VRAM.

        Args:
            process_name (str): Process identifier label for metrics.
            port (int): TCP port for Prometheus HTTP exporter.
            interval (int): Monitoring polling interval in seconds.

        Returns:
            MetricsManager: Configured metrics manager instance.
        """
        metrics_manager = MetricsManager(process_name=process_name, port=port)
        metrics_manager.register_metric("process_cpu_usage_percent", "CPU %")
        metrics_manager.register_metric("process_memory_usage_percent", "Mem %")
        metrics_manager.register_metric("process_memory_rss_bytes", "Process RSS Memory Bytes")
        metrics_manager.register_metric("process_threads_count", "Process Thread Count")
        metrics_manager.register_metric("process_open_fds_count", "Process Open File Descriptors")

        # GPU metrics
        metrics_manager.register_metric("gpu_utilization_percent", "NVIDIA GPU Core Utilization %")
        metrics_manager.register_metric("gpu_memory_utilization_percent", "NVIDIA GPU Memory Utilization %")
        metrics_manager.register_metric("gpu_memory_used_bytes", "NVIDIA GPU VRAM Used Bytes")
        metrics_manager.register_metric("gpu_memory_total_bytes", "NVIDIA GPU VRAM Total Bytes")
        metrics_manager.register_metric("gpu_temperature_celsius", "NVIDIA GPU Temperature °C")
        metrics_manager.register_metric("gpu_power_usage_watts", "NVIDIA GPU Power Draw Watts")

        # PyTorch specific VRAM
        metrics_manager.register_metric("pytorch_vram_allocated_bytes", "PyTorch CUDA Memory Allocated Bytes")
        metrics_manager.register_metric("pytorch_vram_reserved_bytes", "PyTorch CUDA Memory Reserved Bytes")

        try:
            current_process = psutil.Process()
        except Exception as e:
            logging.warning(f"[PROCESS_MONITOR] Failed to obtain current process handle: {e}", exc_info=True)
            return metrics_manager

        def monitor_loop():
            nvml_initialized = False
            if HAS_PYNVML:
                try:
                    pynvml.nvmlInit()
                    nvml_initialized = True
                except Exception as nvml_init_err:
                    logging.debug(f"[PROCESS_MONITOR] NVML initialization skipped/failed: {nvml_init_err}")

            while True:
                try:
                    # Process metrics
                    cpu = current_process.cpu_percent(interval=None)
                    mem = current_process.memory_percent()
                    mem_info = current_process.memory_info()
                    num_threads = current_process.num_threads()
                    try:
                        num_fds = current_process.num_fds()
                    except Exception:
                        num_fds = 0

                    metrics_manager.update_metric("process_cpu_usage_percent", cpu if cpu is not None else 0.0)
                    metrics_manager.update_metric("process_memory_usage_percent", mem)
                    metrics_manager.update_metric("process_memory_rss_bytes", float(mem_info.rss))
                    metrics_manager.update_metric("process_threads_count", float(num_threads))
                    metrics_manager.update_metric("process_open_fds_count", float(num_fds))

                    # GPU hardware metrics via NVML
                    if HAS_PYNVML and nvml_initialized:
                        try:
                            device_count = pynvml.nvmlDeviceGetCount()
                            if device_count > 0:
                                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                                utils = pynvml.nvmlDeviceGetUtilizationRates(handle)
                                mem_info_gpu = pynvml.nvmlDeviceGetMemoryInfo(handle)
                                temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                                power = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0

                                metrics_manager.update_metric("gpu_utilization_percent", float(utils.gpu))
                                metrics_manager.update_metric("gpu_memory_utilization_percent", float(utils.memory))
                                metrics_manager.update_metric("gpu_memory_used_bytes", float(mem_info_gpu.used))
                                metrics_manager.update_metric("gpu_memory_total_bytes", float(mem_info_gpu.total))
                                metrics_manager.update_metric("gpu_temperature_celsius", float(temp))
                                metrics_manager.update_metric("gpu_power_usage_watts", float(power))
                        except Exception as gpu_err:
                            logging.debug(f"[PROCESS_MONITOR] GPU polling exception: {gpu_err}")

                    # PyTorch VRAM metrics (only queried if torch is already imported in this process)
                    if "torch" in sys.modules:
                        try:
                            torch_mod = sys.modules["torch"]
                            if hasattr(torch_mod, "cuda") and torch_mod.cuda.is_available():
                                alloc = torch_mod.cuda.memory_allocated()
                                res = torch_mod.cuda.memory_reserved()
                                metrics_manager.update_metric("pytorch_vram_allocated_bytes", float(alloc))
                                metrics_manager.update_metric("pytorch_vram_reserved_bytes", float(res))
                        except Exception as torch_err:
                            logging.debug(f"[PROCESS_MONITOR] PyTorch VRAM polling exception: {torch_err}")

                except Exception as ex:
                    logging.debug(f"[PROCESS_MONITOR] Monitor loop exception: {ex}")
                    break
                time.sleep(interval)

        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
        logging.info(f"[PROCESS_MONITOR] Started background resource & GPU monitoring for {process_name}.")
        return metrics_manager
