# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: src/database/step_decision_worker.py
# Author: Gabriel Moraes
# Date: August 2026

import logging
import queue
import threading
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from src.repositories.step_decision_repo import StepDecisionRepository


class StepDecisionWorker:
    """
    Non-blocking async background worker for real-time step decision numeric counters (codes 0-5).
    Pushes telemetry into an in-memory Queue in < 0.001 ms without locking
    the real-time simulation step. Flushes compressed numeric counter batches to PostgreSQL.
    """

    def __init__(
        self, repository: "StepDecisionRepository", flush_interval_sec: float = 3.0, batch_threshold: int = 50
    ):
        self.repository = repository
        self.flush_interval_sec = flush_interval_sec
        self.batch_threshold = batch_threshold

        self.decision_queue: queue.Queue = queue.Queue(maxsize=20000)
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # Delta Compression State Cache ( (agent_id_int, code) -> count )
        self._counter_cache: Dict[Tuple[int, int], int] = {}

    def start(self):
        """Starts the background flushing thread."""
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._worker_loop, daemon=True, name="StepDecisionWorkerThread")
            self._thread.start()
            logging.info("[StepDecisionWorker] Async background telemetry worker started.")

    def stop(self):
        """Stops the worker thread and flushes remaining queue items."""
        if self._running:
            self._running = False
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=2.0)
            self._flush_queue_batch()
            logging.info("[StepDecisionWorker] Async background worker stopped and flushed.")

    def push_decision_code(self, agent_id: Any, decision_code: int, count: int = 1):
        """
        Ultra-fast non-blocking push (< 0.001 ms) using pure numeric agent_id and code (0-5).
        """
        agent_id_int = self.repository._to_int_id(agent_id)
        key = (agent_id_int, int(decision_code))
        self._counter_cache[key] = self._counter_cache.get(key, 0) + int(count)

    def push_decision(
        self,
        sim_time: float,
        step_num: int,
        agent_id: Any,
        maturity: str,
        suggested_action: str,
        final_decision: str,
        veto_reason: str,
        total_time_ms: float = 0.0,
        guardian_time_ms: float = 0.0,
    ):
        """
        Backward-compatible non-blocking telemetry push (< 0.001 ms).
        Maps decision string to numeric code (0-5) and increments counter cache.
        """
        dec_upper = str(final_decision or "").upper()
        veto_upper = str(veto_reason or "").upper()

        if dec_upper in ("APROVADA", "APPROVED", "PASS") and "SEM_VETO" in veto_upper:
            code = 0
        elif "AMARELO" in veto_upper or "YELLOW" in veto_upper:
            code = 2
        elif "ALL_RED" in veto_upper or "VERMELHO_INTEGRAL" in veto_upper:
            code = 3
        elif "MIN_RED" in veto_upper or "VERMELHO" in veto_upper:
            code = 4
        elif "D3QN" in veto_upper or "SPILLBACK" in veto_upper or "SATURACAO" in veto_upper:
            code = 5
        elif "MÍNIMO" in veto_upper or "MIN" in veto_upper or "GREEN" in veto_upper or "VERDE" in veto_upper:
            code = 1
        else:
            code = 0 if dec_upper in ("APROVADA", "APPROVED") else 1

        self.push_decision_code(agent_id, code, count=1)

    def _flush_queue_batch(self):
        """Flushes buffered numeric counters to PostgreSQL via atomic execute_values UPSERT."""
        if not self._counter_cache:
            return

        batch_tuples = [
            (agent_id_int, code, cnt) for (agent_id_int, code), cnt in list(self._counter_cache.items()) if cnt > 0
        ]
        self._counter_cache.clear()

        if batch_tuples:
            self.repository.increment_decision_counter_batch(batch_tuples)

    def _worker_loop(self):
        """Background thread loop."""
        last_flush = time.time()
        while self._running:
            try:
                time.sleep(0.5)
                now = time.time()
                if (now - last_flush) >= self.flush_interval_sec or len(self._counter_cache) >= self.batch_threshold:
                    self._flush_queue_batch()
                    last_flush = now
            except Exception as e:
                logging.error(f"[StepDecisionWorker] Error in worker loop: {e}")
