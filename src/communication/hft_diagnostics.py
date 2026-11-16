# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import os
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional


class HFTDiagnostics:
    """
    Handles logging sub-systems and metrics recording for the HFT Link.
    Throttles routine per-frame file writes to 1Hz window summaries with rotating logs.
    """

    def __init__(self, locale_manager=None, summary_interval_sec: float = 1.0):
        self.locale_manager = locale_manager
        self._summary_interval_sec = max(0.25, float(summary_interval_sec))
        self._last_interval_flush = 0.0
        self._last_proc_flush = 0.0
        self._recv_count = 0
        self._recv_max_ms = 0.0
        self._proc_count = 0
        self._proc_max_ms = 0.0
        self.interval_logger = self._setup_interval_logger()
        self.diagnostics_logger = self._setup_diagnostics_logger()

    def _get_string(self, key: str, default: str = None, **kwargs) -> str:
        if self.locale_manager and hasattr(self.locale_manager, "get_string"):
            return self.locale_manager.get_string(key, default=default, **kwargs)
        return default.format(**kwargs) if default and kwargs else (default or key)

    def _setup_interval_logger(self) -> Optional[logging.Logger]:
        """
        Configures a specific logger to write ONLY the inter-arrival times
        to 'logs/hft/hft_inter_arrival.log'.
        """
        try:
            from src.utils.paths import get_base_output_dir

            log_dir = os.path.join(get_base_output_dir(), "logs", "hft")
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, "hft_inter_arrival.log")

            logger = logging.getLogger("HFT_Interval_Logger")
            logger.setLevel(logging.INFO)
            logger.propagate = False  # Prevent propagation to root logger (console)

            if not logger.handlers:
                handler = RotatingFileHandler(log_file, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8")
                formatter = logging.Formatter("%(message)s")
                handler.setFormatter(formatter)
                logger.addHandler(handler)

            return logger
        except Exception as e:
            logging.error(
                self._get_string(
                    "hft_diagnostics.interval_setup_error",
                    default="[HFT] Failed to setup interval logger: {error}",
                    error=e,
                ),
                exc_info=True,
            )
            return None

    def _setup_diagnostics_logger(self) -> Optional[logging.Logger]:
        """
        Configures a dedicated logger for HFT pipeline diagnostics.
        Writes to 'logs/hft/hft_diagnostics.log'.
        """
        try:
            from src.utils.paths import get_base_output_dir

            log_dir = os.path.join(get_base_output_dir(), "logs", "hft")
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, "hft_diagnostics.log")

            logger = logging.getLogger("HFT_Diagnostics_Logger")
            logger.setLevel(logging.INFO)
            logger.propagate = False

            if not logger.handlers:
                handler = RotatingFileHandler(log_file, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8")
                formatter = logging.Formatter("%(message)s")
                handler.setFormatter(formatter)
                logger.addHandler(handler)

            return logger
        except Exception as e:
            logging.error(
                self._get_string(
                    "hft_diagnostics.setup_error", default="[HFT] Failed to setup diagnostics logger: {error}", error=e
                ),
                exc_info=True,
            )
            return None

    def log_recv_delta(self, current_recv_time: float, delta_ms: float, queue_depth: int):
        """Logs throttled inter-arrival telemetry and immediate high-delay warnings."""
        self._recv_count += 1
        if delta_ms > self._recv_max_ms:
            self._recv_max_ms = delta_ms
        now = time.monotonic()
        if (now - self._last_interval_flush) >= self._summary_interval_sec:
            ts_str = datetime.fromtimestamp(current_recv_time).strftime("%H:%M:%S.%f")[:-3]
            if self.interval_logger:
                self.interval_logger.info(
                    f"[{ts_str}] Delta: {delta_ms:.2f} ms (max={self._recv_max_ms:.2f}ms, n={self._recv_count})"
                )
            if self.diagnostics_logger:
                self.diagnostics_logger.info(
                    f"[{ts_str}] recv_delta={delta_ms:.1f}ms max={self._recv_max_ms:.1f}ms | queue_depth={queue_depth}"
                )
            self._last_interval_flush = now
            self._recv_count = 0
            self._recv_max_ms = 0.0

        if delta_ms > 300000:
            logging.warning(
                self._get_string(
                    "hft_diagnostics.delay_warning",
                    default="[HFT] 🔴 Synapse delivery delay: recv_delta={delta:.1f}ms (>300000ms). The delay is on the SYNAPSE/network side.",
                    delta=delta_ms,
                )
            )

    def log_processing(self, recv_time: float, proc_delta_ms: float, queue_depth: int, backpressure_threshold: int):
        """Logs throttled controller processing diagnostics and immediate SLA warnings."""
        self._proc_count += 1
        if proc_delta_ms > self._proc_max_ms:
            self._proc_max_ms = proc_delta_ms
        now = time.monotonic()
        if (now - self._last_proc_flush) >= self._summary_interval_sec:
            if self.diagnostics_logger:
                ts_str = datetime.fromtimestamp(recv_time).strftime("%H:%M:%S.%f")[:-3]
                self.diagnostics_logger.info(
                    f"[{ts_str}] proc_delta={proc_delta_ms:.1f}ms max={self._proc_max_ms:.1f}ms n={self._proc_count} | queue_depth={queue_depth}"
                )
            self._last_proc_flush = now
            self._proc_count = 0
            self._proc_max_ms = 0.0

        if queue_depth > backpressure_threshold:
            logging.warning(
                self._get_string(
                    "hft_diagnostics.backpressure_warning",
                    default="[HFT] ⚠️ Backpressure detected! queue_depth={depth} (>{thresh}). CARINA processing can't keep up.",
                    depth=queue_depth,
                    thresh=backpressure_threshold,
                )
            )

        if proc_delta_ms > 100:
            logging.warning(
                self._get_string(
                    "hft_diagnostics.slow_processing_warning",
                    default="[HFT] ⏱️ Slow frame processing: {delta:.1f}ms (>100ms threshold). CARINA-side bottleneck.",
                    delta=proc_delta_ms,
                )
            )
