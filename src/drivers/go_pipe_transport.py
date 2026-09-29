# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# File: src/drivers/go_pipe_transport.py
# Author: Gabriel Moraes
# Date: 2026-09-25

"""
NDJSON message framing and thread-safe IPC pipe communication over standard I/O.
Isolated responsibility according to the Single Responsibility Principle (SRP).
"""

import json
import logging
import subprocess
import threading
from typing import Any, Callable, Dict, Optional, Tuple

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

    def start_stdout_reader(self, process: subprocess.Popen) -> None:
        """Starts background reader thread for the given process stdout stream."""
        self._reading = True
        self._stdout_thread = threading.Thread(
            target=self._read_stdout_loop,
            args=(process,),
            daemon=True,
            name="GoGatewayStdoutReader",
        )
        self._stdout_thread.start()

    def stop(self) -> None:
        """Stops the transport reader and wakes up any pending requests."""
        self._reading = False
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
        if not process or not process.stdin:
            raise RuntimeError("Go Gateway process is not running or stdin is closed")

        line = json.dumps(payload) + "\n"
        with self._write_lock:
            process.stdin.write(line)
            process.stdin.flush()

    def send_command(
        self,
        process: Optional[subprocess.Popen],
        cmd: str,
        timeout: float = 3.0,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Sends a synchronous command over stdin and waits for its corresponding response on stdout.
        """
        if not process or not process.stdin:
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
                    logger.warning(f"[GoPipeTransport] Non-JSON line on stdout: {line_str} ({parse_err})")
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

                # 2. Unsolicited Push Event (Traps UDP 162 or Heartbeat changes)
                elif msg_type == "event":
                    if self.on_event_received:
                        self.on_event_received(msg)

            except Exception as e:
                if self._reading:
                    logger.error(f"[GoPipeTransport] Error reading stdout: {e}")
                break
