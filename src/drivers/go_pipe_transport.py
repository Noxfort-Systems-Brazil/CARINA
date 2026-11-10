# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
NDJSON message framing and thread-safe IPC pipe communication over standard I/O.
Isolated responsibility according to the Single Responsibility Principle (SRP).
"""

import json
import logging
import subprocess
import threading
from typing import Any, Callable, Dict, Optional, Tuple

from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class GoPipeTransport:
    """
    Handles request-response correlation and message framing over OS standard pipes (NDJSON).
    """

    def __init__(self, on_event_received: Optional[Callable[[Dict[str, Any]], None]] = None) -> None:
        self.on_event_received = on_event_received
        self._req_counter = 0
        self._counter_lock = threading.Lock()
        self._write_lock = threading.Lock()
        self._pending_requests: Dict[int, Tuple[threading.Event, Dict[str, Any]]] = {}
        self._pending_lock = threading.Lock()
        self._stdout_thread: Optional[threading.Thread] = None
        self._reading = False
        self._event_executor: Optional[ThreadPoolExecutor] = None

    def start_stdout_reader(self, process: subprocess.Popen) -> None:
        """Starts background reader thread for the given process stdout stream."""
        self._reading = True
        self._event_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="GoPipeEventWorker")
        self._stdout_thread = threading.Thread(
            target=self._read_stdout_loop,
            args=(process,),
            daemon=True,
            name="GoGatewayStdoutReader",
        )
        self._stdout_thread.start()

    def is_connected(self, process: Optional[subprocess.Popen] = None) -> bool:
        """Checks if transport is connected to running subprocess stdin/stdout."""
        return process is not None and process.stdin is not None and process.poll() is None

    def stop(self) -> None:
        """Stops the transport reader and wakes up any pending requests."""
        self._reading = False
        if self._event_executor:
            try:
                self._event_executor.shutdown(wait=False, cancel_futures=True)
            except Exception as _exc:
                logger.debug("[drivers] Ignored recoverable error: %s", _exc)
            self._event_executor = None
        with self._pending_lock:
            for evt, box in self._pending_requests.values():
                box["res"] = {"success": False, "error": "Transport stopped"}
                evt.set()
            self._pending_requests.clear()

    def _next_id(self) -> int:
        with self._counter_lock:
            self._req_counter += 1
            return self._req_counter

    def send_raw(self, process: Optional[subprocess.Popen], payload: Dict[str, Any]) -> None:
        """Sends raw JSON line through process.stdin."""
        line = json.dumps(payload) + "\n"
        with self._write_lock:
            if process and process.stdin:
                process.stdin.write(line)
                process.stdin.flush()
            else:
                raise RuntimeError("Go Gateway process is not running or stdin is closed")

    def send_command(
        self,
        process: Optional[subprocess.Popen],
        cmd: str,
        timeout: float = 3.0,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Sends a synchronous command over socket or stdin and waits for its corresponding response.
        """
        if not self.is_connected(process):
            return {"success": False, "error": "Processo Go não está ativo"}

        req_id = self._next_id()
        payload = {"id": req_id, "cmd": cmd, **kwargs}

        evt = threading.Event()
        response_box: Dict[str, Any] = {}

        with self._pending_lock:
            self._pending_requests[req_id] = (evt, response_box)

        try:
            self.send_raw(process, payload)
            signaled = evt.wait(timeout=timeout)
            if not signaled:
                logger.error(f"[GoPipeTransport] Command '{cmd}' timed out after {timeout}s (ID: {req_id})")
                return {"success": False, "error": f"Timeout após {timeout}s"}
            return response_box.get("res", {"success": False, "error": "Resposta vazia"})
        finally:
            with self._pending_lock:
                self._pending_requests.pop(req_id, None)

    def _read_stdout_loop(self, process: subprocess.Popen) -> None:
        """Reads NDJSON messages from process.stdout."""
        while self._reading and process and process.stdout:
            try:
                line = process.stdout.readline()
                if not line:
                    break

                line_str = line.strip()
                if not line_str:
                    continue

                try:
                    msg = json.loads(line_str)
                except Exception as parse_err:
                    logger.warning(f"[GoPipeTransport] Non-JSON line on stdout: {line_str} ({parse_err})", exc_info=True)
                    continue

                msg_type = msg.get("type")

                # 1. Command Response
                if msg_type == "response":
                    req_id = msg.get("id")
                    with self._pending_lock:
                        if req_id in self._pending_requests:
                            evt, box = self._pending_requests[req_id]
                            box["res"] = msg
                            evt.set()

                # 2. Unsolicited Push Event (Traps UDP 162, Heartbeat changes, or EVP telemetry)
                elif msg_type in ("event", "evp_telemetry"):
                    if self.on_event_received:
                        if self._event_executor:
                            try:
                                self._event_executor.submit(self._dispatch_event_safe, msg)
                            except Exception as submit_err:
                                logger.error(f"[GoPipeTransport] Falha ao enfileirar evento assíncrono: {submit_err}", exc_info=True)
                        else:
                            # Safe fallback in case executor has already been shut down
                            threading.Thread(target=self._dispatch_event_safe, args=(msg,), daemon=True).start()

            except Exception as e:
                if self._reading:
                    logger.error(f"[GoPipeTransport] Error reading stdout: {e}", exc_info=True)
                break

    def _dispatch_event_safe(self, msg: Dict[str, Any]) -> None:
        """Dispatches push events to subscriber safely catching any exceptions."""
        try:
            if self.on_event_received:
                self.on_event_received(msg)
        except Exception as e:
            logger.error(f"[GoPipeTransport] Error handling unsolicited push event: {e}", exc_info=True)
