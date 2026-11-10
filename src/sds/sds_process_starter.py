# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Singleton manager to ensure the activation of the SDS process (DashboardService + CCO Flet Web)
when the interface is launched independently or in development mode.
"""

import atexit
import configparser
import logging
import multiprocessing
import os
import sys
import threading
import time
import urllib.request
from typing import Optional

logger = logging.getLogger(__name__)


class SDSProcessStarter:
    """
    Supervises the SDS/CCO lifecycle in standalone mode (SRP).
    Ensures no duplication occurs if the CARINA Orchestrator has already started the SDS.
    """

    _instance: Optional["SDSProcessStarter"] = None
    _instance_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "SDSProcessStarter":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self) -> None:
        self._process: Optional[multiprocessing.Process] = None
        self._sds_q: Optional[multiprocessing.Queue] = None
        self._ui_cmd_q: Optional[multiprocessing.Queue] = None
        self._started_by_us = False
        self._lock = threading.Lock()
        atexit.register(self.stop)

    def is_port_active(self, port: int = 2201, timeout: float = 0.5) -> bool:
        """Checks if an HTTP service is responding on the specified port."""
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{port}/")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status in (200, 302, 307)
        except Exception:
            return False

    def is_process_running(self) -> bool:
        """Checks if the standalone SDS process is active."""
        return self._process is not None and self._process.is_alive()

    def is_orchestrator_running(self) -> bool:
        """Checks if SDS is already running via CARINA Orchestrator (ProcessManager)."""
        try:
            import psutil

            current_pid = os.getpid()
            for proc in psutil.process_iter(attrs=["pid", "name", "cmdline"]):
                try:
                    if proc.info["pid"] == current_pid:
                        continue
                    name = proc.info.get("name") or ""
                    cmdline = " ".join(proc.info.get("cmdline") or [])
                    if "DashboardService" in name or "dashboard_worker" in cmdline:
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception:
            pass
        return False

    def start_if_not_running(self, port: int = 2201) -> bool:
        """Starts the standalone SDS process if not already running."""
        with self._lock:
            if self.is_port_active(port=port) or self.is_process_running() or self.is_orchestrator_running():
                return True

            logger.info("[SDSProcessStarter] Iniciando processo autônomo do SDS...")
            from sds.dashboard_worker import run_sds_worker
            from utils.paths import resource_path

            settings = configparser.ConfigParser()
            settings_path = resource_path(os.path.join("config", "settings.ini"))
            if os.path.exists(settings_path):
                settings.read(settings_path, encoding="utf-8")

            # Retain strong references on self so GC does not unlink semaphores in spawn mode
            self._sds_q = multiprocessing.Queue(maxsize=200)
            self._ui_cmd_q = multiprocessing.Queue(maxsize=200)

            self._process = multiprocessing.Process(
                target=run_sds_worker,
                args=(self._sds_q, settings, self._ui_cmd_q),
                name="DashboardService_Standalone",
                daemon=True,
            )
            self._process.start()
            self._started_by_us = True

            # Wait for process initialization (up to 2 seconds)
            for _ in range(10):
                time.sleep(0.1)
                if self._process.is_alive():
                    logger.info(f"[SDSProcessStarter] ✅ Processo SDS ativado com sucesso (PID {self._process.pid}).")
                    return True

            return self._process.is_alive()

    def stop(self) -> None:
        """Terminates the standalone process if started by this instance."""
        with self._lock:
            if self._process is not None and self._started_by_us:
                try:
                    if self._process.is_alive():
                        logger.info(f"[SDSProcessStarter] Encerrando processo autônomo do SDS (PID {self._process.pid})...")
                        self._process.terminate()
                        self._process.join(timeout=1.5)
                        if self._process.is_alive():
                            self._process.kill()
                except Exception as err:
                    logger.debug(f"[SDSProcessStarter] Exceção ao encerrar processo SDS: {err}")
                finally:
                    self._process = None
                    self._started_by_us = False

            if self._sds_q is not None:
                try:
                    self._sds_q.close()
                except Exception:
                    pass
                self._sds_q = None

            if self._ui_cmd_q is not None:
                try:
                    self._ui_cmd_q.close()
                except Exception:
                    pass
                self._ui_cmd_q = None
