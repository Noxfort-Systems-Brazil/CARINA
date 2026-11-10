# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import socket
import sys
import threading
import time


class SingleInstanceLock:
    """
    Manages single-instance lock via TCP Socket (127.0.0.1:42123).
    Allows triggering a UI restore on an active instance when launching a second one.
    """

    def __init__(self, port: int = 42123, host: str = "127.0.0.1"):
        self.host = host
        self.port = port
        self.server_socket = None
        self.listener_thread = None

    def acquire(self) -> bool:
        """
        Attempts to bind to the single instance port.
        If port binding fails, notifies the active instance to restore UI and returns False.
        """
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            return True
        except socket.error:
            # Second instance detected
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect((self.host, self.port))
                s.sendall(b"restore_ui")
                s.close()
            except Exception as e:
                print(f"Error communicating UI restore request: {e}")
            print("Another instance of CARINA is already running! Requesting UI restore...")
            return False

    def start_restore_listener(self, shutdown_requested: threading.Event, restore_requested: threading.Event):
        """
        Launches a background thread listening for UI restore requests from secondary instances.
        """

        def listener_loop():
            while not shutdown_requested.is_set():
                try:
                    self.server_socket.settimeout(1.0)
                    try:
                        conn, addr = self.server_socket.accept()
                    except socket.timeout:
                        continue
                    data = conn.recv(1024)
                    if data == b"restore_ui":
                        logging.info("[SingleInstance] Received UI restore request from another instance.")
                        restore_requested.set()
                    conn.close()
                except Exception as e:
                    if not shutdown_requested.is_set():
                        logging.error(f"[SingleInstance] Error in single instance listener: {e}", exc_info=True)
                    time.sleep(0.5)

        self.listener_thread = threading.Thread(target=listener_loop, name="SingleInstanceListenerThread", daemon=True)
        self.listener_thread.start()

    def release(self):
        """
        Closes the single instance socket gracefully.
        """
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
            self.server_socket = None
