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

# File: ui/providers/live_data_provider.py (Pure In-Memory IPC / Zero-Port Edition)
# Author: Gabriel Moraes
# Date: 2026

"""
Defines the LiveDataProvider using multiprocessing.Queue for 100% in-memory IPC.

This implementation completely eliminates the WebSocket TCP port 8765,
providing zero-port, sub-millisecond bidirectional communication between
the CARINA UI and the backend processes.
"""

import logging
import queue
import threading
from typing import Any, Callable, Dict, Optional


class LiveDataProvider:
    """
    A service that connects the UI directly to the back-end via multiprocessing.Queue
    to provide real-time simulation data packets and send commands with zero network ports.
    """

    GLOBAL_SHUTDOWN_EVENT = None
    CACHED_INITIAL_GEOMETRY: Optional[Dict[str, Any]] = None

    def __init__(
        self,
        on_data_received: Callable[[Dict[str, Any]], None],
        shutdown_event: Optional[threading.Event] = None,
        ui_telemetry_queue: Optional[Any] = None,
        ui_command_queue: Optional[Any] = None,
    ):
        self.on_data_received = on_data_received
        self.shutdown_event = shutdown_event
        self.ui_telemetry_queue = ui_telemetry_queue
        self.ui_command_queue = ui_command_queue

        self._thread: Optional[threading.Thread] = None
        self._is_running = False

    @property
    def is_stopped(self) -> bool:
        """Returns True if the provider has been stopped or system shutdown is requested."""
        if not self._is_running:
            return True
        if self.shutdown_event and self.shutdown_event.is_set():
            return True
        if LiveDataProvider.GLOBAL_SHUTDOWN_EVENT and LiveDataProvider.GLOBAL_SHUTDOWN_EVENT.is_set():
            return True
        return False

    def _resolve_queues(self):
        """Dynamically resolves IPC queues from ui.main_ui if not provided at instantiation."""
        if self.ui_telemetry_queue is None or self.ui_command_queue is None:
            try:
                import sys

                for mod_name in ["ui.main_ui", "main_ui"]:
                    if mod_name in sys.modules:
                        ui_mod = sys.modules[mod_name]
                        if self.ui_telemetry_queue is None:
                            self.ui_telemetry_queue = getattr(ui_mod, "ui_telemetry_queue", None)
                        if self.ui_command_queue is None:
                            self.ui_command_queue = getattr(ui_mod, "ui_command_queue", None)
                        break
            except Exception as e:
                logging.debug(f"[LiveDataProvider] Error resolving queues dynamically: {e}")

    def start(self):
        """Starts the IPC queue listening thread and sends initial handshake commands."""
        self._resolve_queues()

        if not self._thread or not self._thread.is_alive():
            self._is_running = True

            # If we already have a cached geometry packet (e.g., UI reopened from system tray), dispatch immediately
            if LiveDataProvider.CACHED_INITIAL_GEOMETRY and self.on_data_received:
                try:
                    logging.info("[LiveDataProvider] Re-dispatching cached map geometry to new/restored UI view.")
                    self.on_data_received(LiveDataProvider.CACHED_INITIAL_GEOMETRY)
                except Exception as ex:
                    logging.warning(f"[LiveDataProvider] Error dispatching cached geometry: {ex}")

            self._thread = threading.Thread(target=self._listen_loop, name="LiveDataProviderIPCThread", daemon=True)
            self._thread.start()
            logging.info("[LiveDataProvider] Pure in-memory IPC listener thread started (Zero Ports).")

            # Initial status checks
            self.send_command_to_backend({"type": "check_lockdown"})

    def stop(self):
        """Stops the listening thread cleanly."""
        self._is_running = False
        if self._thread and self._thread.is_alive() and threading.current_thread() != self._thread:
            try:
                self._thread.join(timeout=1.0)
            except Exception:
                pass
        logging.info("[LiveDataProvider] LiveDataProvider stopped.")

    def _listen_loop(self):
        """Continuous listener loop consuming telemetry packets from ui_telemetry_queue."""
        logging.info("[LiveDataProvider] Entering IPC queue reading loop...")

        while not self.is_stopped:
            self._resolve_queues()
            q = self.ui_telemetry_queue

            if q is None:
                # Passive wait if queue is not yet injected
                for _ in range(5):
                    if self.is_stopped:
                        break
                    threading.Event().wait(0.1)
                continue

            try:
                data_packet = q.get(block=True, timeout=0.2)

                if data_packet is None or data_packet == "STOP":
                    logging.info("[LiveDataProvider] Stop sentinel received from telemetry queue.")
                    break

                if isinstance(data_packet, dict):
                    # Cache map geometry packet for instant recovery if UI restores
                    if data_packet.get("type") == "initial_map_geometry":
                        LiveDataProvider.CACHED_INITIAL_GEOMETRY = data_packet

                    if self.on_data_received:
                        self.on_data_received(data_packet)

            except queue.Empty:
                continue
            except (EOFError, BrokenPipeError):
                logging.info("[LiveDataProvider] IPC Queue closed or pipe broken.")
                break
            except Exception as e:
                if not self.is_stopped:
                    logging.debug(f"[LiveDataProvider] Exception reading IPC queue: {e}")

        logging.info("[LiveDataProvider] Exited IPC queue reading loop.")

    def send_command_to_backend(self, command: dict):
        """
        Sends a command (Python dictionary) directly to CentralController
        via multiprocessing.Queue without network serialization.
        """
        self._resolve_queues()
        q = self.ui_command_queue

        if q is not None:
            try:
                q.put(command)
                logging.debug(f"[LiveDataProvider] Command dispatched to ui_command_queue: {command.get('type')}")
            except Exception as e:
                logging.warning(f"[LiveDataProvider] Failed to put command into queue: {e}")
        else:
            logging.warning(
                f"[LiveDataProvider] Attempting to send command '{command.get('type')}' without an active ui_command_queue."
            )
