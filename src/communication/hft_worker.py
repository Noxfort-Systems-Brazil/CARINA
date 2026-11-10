# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import queue
import threading
import time
from typing import Optional

from src.communication.hft_diagnostics import HFTDiagnostics


class HFTWorker:
    """
    Manages the Cold Path of the HFT pipeline. Dequeues frames
    from the hot gRPC thread and passes them to the Controller to be processed.
    """

    _BACKPRESSURE_THRESHOLD = 10

    def __init__(self, controller, diagnostics: HFTDiagnostics, server_ref, locale_manager=None):
        self.controller = controller
        self.diagnostics = diagnostics
        self.server_ref = server_ref  # To check if server state is "RUNNING"
        self.locale_manager = locale_manager

        self.frame_queue: queue.Queue = queue.Queue(maxsize=100)
        self._worker_thread: Optional[threading.Thread] = None
        self._worker_running = threading.Event()

    def _get_string(self, key: str, default: str = None, **kwargs) -> str:
        if self.locale_manager and hasattr(self.locale_manager, "get_string"):
            return self.locale_manager.get_string(key, default=default, **kwargs)
        return default.format(**kwargs) if default and kwargs else (default or key)

    def get_queue_depth(self) -> int:
        return self.frame_queue.qsize()

    def enqueue(self, frame, current_recv_time):
        """
        Enqueues a frame for async processing.
        """
        try:
            self.frame_queue.put_nowait((frame, current_recv_time))
        except queue.Full:
            logging.error(
                self._get_string(
                    "hft_worker.queue_full",
                    default="[HFT] ❌ Frame queue FULL! Dropping frame. CARINA processing is critically overloaded.",
                )
            )

    def start(self):
        """Starts the dedicated frame processing worker thread."""
        if self._worker_thread is not None and self._worker_thread.is_alive():
            return

        self._worker_running.set()
        self._worker_thread = threading.Thread(target=self._worker_loop, name="HFT-FrameWorker", daemon=True)
        self._worker_thread.start()
        logging.info(self._get_string("hft_worker.started", default="[HFT Worker] Async worker thread started."))

    def stop(self):
        """Signals the worker thread to stop gracefully."""
        self._worker_running.clear()
        try:
            self.frame_queue.put(None, timeout=0.1)
        except queue.Full:
            pass

    def _worker_loop(self):
        """
        Worker loop: dequeues frames and processes them via the controller.
        """
        logging.info(self._get_string("hft_worker.loop_running", default="[HFT] 🔄 Frame Worker Loop running."))

        while self._worker_running.is_set():
            try:
                frame_item = self.frame_queue.get(timeout=0.5)

                if frame_item is None:
                    break

                frame, recv_time = frame_item

                t_proc_start = time.perf_counter()

                if getattr(self.server_ref, "state", None) == "RUNNING":
                    self.controller.process_traffic_frame(frame)

                t_proc_end = time.perf_counter()
                proc_delta_ms = (t_proc_end - t_proc_start) * 1000

                current_depth = self.get_queue_depth()
                self.diagnostics.log_processing(recv_time, proc_delta_ms, current_depth, self._BACKPRESSURE_THRESHOLD)

            except queue.Empty:
                continue
            except Exception as e:
                logging.error(
                    self._get_string(
                        "hft_worker.processing_error", default="[HFT Worker] Error processing frame: {error}", error=e
                    )
                , exc_info=True)

        logging.info(self._get_string("hft_worker.stopped", default="[HFT Worker] Worker thread stopped."))
