# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
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

# File: src/launcher/process_reaper.py
# Author: Gabriel Moraes
# Date: September 2026

import logging
import multiprocessing
import os
import signal
import sys
import time
from typing import Any, Dict, List, Optional

import psutil


class ProcessReaper:
    """Encapsulates process termination, child tree walk, signal propagation, and zombie cleanup."""

    @classmethod
    def shutdown_all(
        cls,
        controller_conn: Optional[Any],
        ai_conn: Optional[Any],
        queues: Dict[str, Any],
        processes: List[multiprocessing.Process],
    ) -> None:
        """Performs graceful shutdown and total cleanup without hanging or leaving zombie processes."""
        logging.info("Starting graceful shutdown and total system cleanup...")

        # 1. Signal CentralController and AI_Process to terminate services
        try:
            if controller_conn:
                controller_conn.send(("system", "shutdown", (), {}))
            if ai_conn:
                ai_conn.send(("system", "shutdown", (), {}))
            logging.info("Shutdown signal sent to CentralController and AI_Process.")
        except Exception as e:
            logging.error(f"Error shutting down IPC connections: {e}")

        # 1b. Signal Go Hardware Gateway to release all controls and terminate
        try:
            from src.drivers.go_gateway_client import GoGatewayClient

            GoGatewayClient.get_instance().stop()
        except Exception:
            pass

        # 2. Notify queues with sentinel values (None and 'STOP')
        for q_key, q in queues.items():
            try:
                q.put(None)
                q.put("STOP")
            except Exception:
                pass

        # 3. Give worker processes a brief window to exit cleanly
        time.sleep(0.3)

        # 4. Terminate Python active multiprocessing children
        try:
            for child in multiprocessing.active_children():
                try:
                    child.terminate()
                except Exception:
                    pass
        except Exception:
            pass

        # 5. Dynamically capture full child process tree BEFORE sending termination signals
        all_children = []
        try:
            current_proc = psutil.Process(os.getpid())
            for child in current_proc.children(recursive=True):
                try:
                    cmdline = " ".join(child.cmdline()) if hasattr(child, "cmdline") else ""
                    if "resource_tracker" not in cmdline:
                        all_children.append(child)
                except Exception:
                    pass
        except Exception:
            pass

        # 6. Send SIGTERM to primary process handles and child process tree
        for p in processes:
            if p.is_alive():
                try:
                    p.terminate()
                except Exception:
                    pass

        if all_children:
            for child in all_children:
                try:
                    if child.is_running():
                        child.terminate()
                except (psutil.NoSuchProcess, psutil.ZombieProcess):
                    pass

        # 7. Wait briefly for processes to exit after SIGTERM, then SIGKILL any stubborn processes
        procs_dict = {}
        for p in processes:
            if p.pid and p.is_alive():
                try:
                    procs_dict[p.pid] = psutil.Process(p.pid)
                except (psutil.NoSuchProcess, psutil.ZombieProcess):
                    pass

        if all_children:
            for child in all_children:
                try:
                    if child.is_running() and child.pid not in procs_dict:
                        procs_dict[child.pid] = child
                except (psutil.NoSuchProcess, psutil.ZombieProcess):
                    pass

        procs_to_wait = list(procs_dict.values())
        if procs_to_wait:
            gone, alive = psutil.wait_procs(procs_to_wait, timeout=0.4)
            for p_alive in alive:
                try:
                    proc_name = p_alive.name() if callable(getattr(p_alive, "name", None)) else "Process"
                    logging.warning(f"Forcing termination of process {p_alive.pid} ({proc_name}) via SIGKILL.")
                    p_alive.kill()
                except (psutil.NoSuchProcess, psutil.ZombieProcess):
                    pass

        # 8. Reap all multiprocessing.Process handles via join()
        for p in processes:
            try:
                p.join(timeout=0.2)
            except Exception:
                pass

        # 9. Process Group Kill (Linux/Unix)
        if sys.platform != "win32":
            try:
                pgid = os.getpgrp()
                current_pid = os.getpid()
                for proc in psutil.process_iter(["pid", "pgid", "cmdline"]):
                    try:
                        if proc.info["pgid"] == pgid and proc.info["pid"] != current_pid:
                            cmdline = " ".join(proc.info.get("cmdline") or [])
                            if "resource_tracker" not in cmdline:
                                os.kill(proc.info["pid"], signal.SIGKILL)
                    except Exception:
                        pass
            except Exception:
                pass

        # 10. Explicitly close all IPC queues
        for q_key, q in queues.items():
            try:
                q.close()
                q.cancel_join_thread()
            except Exception:
                pass

        logging.info("CARINA system fully shutdown with no zombie processes.")
