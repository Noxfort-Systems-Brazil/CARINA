# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import os
import threading
import time
from typing import Callable, Optional


class MfdAnalysisClient:
    """
    Listens to the MFD analysis IPC result queue in a separate thread,
    guaranteeing 100% in-memory IPC communication without creating cache or request files on disk,
    mirroring the exact architecture of InfrastructureClient (SAS Engine).
    """

    def __init__(
        self,
        on_analysis_complete_callback: Callable[[dict], None],
        results_dir: Optional[str] = None,
        mfd_result_queue=None,
        mfd_trigger_queue=None,
    ):
        self.on_analysis_complete = on_analysis_complete_callback
        self.results_dir = results_dir
        self.mfd_result_queue = mfd_result_queue
        self.mfd_trigger_queue = mfd_trigger_queue

    def start_analysis(self):
        """
        Puts an MFD trigger packet into mfd_trigger_queue and starts listening for MFD optimization results in memory.
        Returns immediately. The result will be delivered via the callback.
        """
        # Resolve mfd_trigger_queue if not explicitly provided
        trig_queue = self.mfd_trigger_queue
        if trig_queue is None:
            try:
                import ui.main_ui as ui_module

                trig_queue = getattr(ui_module, "mfd_trigger_queue", None)
            except Exception:
                pass

        if trig_queue is not None:
            try:
                trig_queue.put(("trigger_mfd", {}))
                logging.info(
                    "[MfdAnalysisClient] Pacote de disparo MFD enviado com sucesso para mfd_trigger_queue em memória."
                )
            except Exception as ex:
                logging.error(f"[MfdAnalysisClient] Erro ao enviar disparo para mfd_trigger_queue: {ex}", exc_info=True)

        trigger_time = time.time()
        thread = threading.Thread(target=self._fetch_thread_target, args=(trigger_time,), daemon=True)
        thread.start()

    def _fetch_thread_target(self, trigger_time: float = None):
        result = {}
        time_margin = 2.0
        min_valid_timestamp = (trigger_time - time_margin) if trigger_time is not None else 0.0

        # Dynamically resolve mfd_result_queue if not provided at instantiation
        queue = self.mfd_result_queue
        if queue is None:
            try:
                import ui.main_ui as ui_module

                queue = getattr(ui_module, "mfd_result_queue", None)
            except Exception as ex:
                logging.error(f"[MfdAnalysisClient] Error resolving mfd_result_queue dynamically: {ex}", exc_info=True)

        if queue is None:
            logging.error("[MfdAnalysisClient] mfd_result_queue is NULL. Cannot receive in-memory IPC results.")
            result = {
                "status": "error",
                "message": "Fila IPC de resultados MFD (mfd_result_queue) não foi conectada pela interface.",
            }
            if self.on_analysis_complete:
                self.on_analysis_complete(result)
            return

        logging.info(
            "[MfdAnalysisClient] Starting asynchronous in-memory IPC queue poll for MFD report (no timeout)..."
        )

        # Drain all stale messages from queue before polling for new job result
        try:
            while not queue.empty():
                queue.get_nowait()
        except Exception:
            pass

        try:
            ipc_result = queue.get(block=True)
            if isinstance(ipc_result, dict):
                logging.info(
                    f"[MfdAnalysisClient] Success: New MFD report received via in-memory IPC queue (status={ipc_result.get('status')})."
                )
                result = ipc_result
            else:
                result = {"status": "error", "message": "Formato inválido retornado da fila IPC de resultados MFD."}
        except Exception as poll_err:
            logging.error(f"[MfdAnalysisClient] Error reading MFD result from IPC queue: {poll_err}", exc_info=True)
            result = {"status": "error", "message": f"Erro na recepção do resultado MFD: {poll_err}"}

        if self.on_analysis_complete:
            self.on_analysis_complete(result)
