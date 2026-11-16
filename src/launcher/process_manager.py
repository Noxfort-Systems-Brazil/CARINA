# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import configparser
import logging
import os
import sys
import threading
from multiprocessing import Pipe, Process, Queue

try:
    from launcher.backend_service_registry import start_backend_worker_processes
    from launcher.fenix_supervision_loop import FenixSupervisionController
    from launcher.process_reaper import ProcessReaper
    from launcher.worker_entrypoints import execute_controller_process, resolve_legacy_worker_attribute
except ImportError:
    from src.launcher.backend_service_registry import start_backend_worker_processes
    from src.launcher.fenix_supervision_loop import FenixSupervisionController
    from src.launcher.process_reaper import ProcessReaper
    from src.launcher.worker_entrypoints import execute_controller_process, resolve_legacy_worker_attribute

from utils.logging_setup import setup_logging
from utils.paths import get_base_output_dir, resource_path
from utils.process_monitor import ProcessMonitor

# Re-exports for backward compatibility
__all__ = ["ProcessManager", "run_controller_process", "ProcessReaper"]


def __getattr__(name: str):
    """Lazy resolver for legacy module-level worker attributes (PEP 562)."""
    return resolve_legacy_worker_attribute(__name__, name)


def run_controller_process(settings, pipe_conn, wd_q, sds_q, sas_q, ui_q, mfd_trigger_q=None, fenix_q=None):
    """Target function for isolated execution of CentralController."""
    execute_controller_process(
        settings,
        pipe_conn,
        wd_q,
        sds_q,
        sas_q,
        ui_q,
        mfd_trigger_q=mfd_trigger_q,
        fenix_q=fenix_q,
        caller_module=sys.modules[__name__],
    )


class ProcessManager:
    """
    Facade orchestrating IPC queues, backend worker startup, F.E.N.I.X. supervision,
    and graceful multi-process shutdown via specialized collaborators.
    """

    def __init__(self):
        self.settings = None
        self.queues = {}
        self.processes = []
        self.controller_conn = None
        self.ai_conn = None
        self.p_cc = None
        self.p_ai = None
        self.fenix_supervisor = None
        self._stop_fenix_supervision = threading.Event()
        self._fenix_controller = self._build_fenix_controller()
        self._fenix_supervision_thread = None

    def _build_fenix_controller(self) -> FenixSupervisionController:
        return FenixSupervisionController(
            get_queues=lambda: getattr(self, "queues", {}),
            get_processes=lambda: getattr(self, "processes", []),
            get_supervisor=lambda: getattr(self, "fenix_supervisor", None),
            on_ai_resurrected=self._set_ai_process,
            get_stop_event=lambda: getattr(self, "_stop_fenix_supervision", None),
        )

    def _ensure_fenix_controller(self) -> FenixSupervisionController:
        ctrl = getattr(self, "_fenix_controller", None)
        if ctrl is None:
            ctrl = self._build_fenix_controller()
            self._fenix_controller = ctrl
        return ctrl

    def _set_ai_process(self, new_proc) -> None:
        self.p_ai = new_proc

    def load_settings(self):
        """Loads and validates the settings.ini configuration file."""
        self.settings = configparser.ConfigParser()
        settings_path = resource_path(os.path.join("config", "settings.ini"))
        if not self.settings.read(settings_path, encoding="utf-8"):
            logging.critical(f"Settings not found at: {settings_path}")
            sys.exit(1)
        return self.settings

    def setup_queues_and_pipes(self):
        """Initializes IPC Pipe connections and multiprocessing Queues."""
        self.controller_conn, self.ai_conn = Pipe()
        self.queues = {
            "wd": Queue(maxsize=500),
            "fenix": Queue(maxsize=50),
            "sds": Queue(maxsize=500),
            "sas": Queue(maxsize=500),
            "ui": Queue(maxsize=500),
            "db": Queue(maxsize=500),
            "g_state": Queue(maxsize=500),
            "g_signal": Queue(maxsize=500),
            "sas_results": Queue(maxsize=10),
            "mfd_results": Queue(maxsize=10),
            "mfd_trigger": Queue(maxsize=10),
            "ui_telemetry": Queue(maxsize=500),
        }

    def start_all_backend_services(self):
        """Launches all CARINA backend processes."""
        if not self.settings:
            self.load_settings()

        self.setup_queues_and_pipes()
        logging.info("Starting BACKEND processes...")

        processes, p_cc, p_ai, fenix_supervisor = start_backend_worker_processes(
            process_cls=Process,
            controller_target=run_controller_process,
            settings=self.settings,
            controller_conn=self.controller_conn,
            ai_conn=self.ai_conn,
            queues=self.queues,
        )
        self.processes = processes
        self.p_cc = p_cc
        self.p_ai = p_ai
        self.fenix_supervisor = fenix_supervisor

        self._start_fenix_supervision()
        logging.info(f"All {len(self.processes)} BACKEND processes started. (Launcher PID: {os.getpid()})")

    def _start_fenix_supervision(self):
        """Starts background supervisor thread listening for FENIX recovery triggers."""
        ctrl = self._ensure_fenix_controller()
        ctrl.start()
        self._fenix_supervision_thread = ctrl.thread

    def _fenix_supervision_loop(self):
        """Listens on fenix IPC queue and handles resurrection requests."""
        self._ensure_fenix_controller().run_loop()

    def shutdown_all(self):
        """Delegates graceful shutdown and process tree cleanup to ProcessReaper."""
        ctrl = self._ensure_fenix_controller()
        ctrl.stop()
        self._fenix_supervision_thread = ctrl.thread

        ProcessReaper.shutdown_all(
            controller_conn=self.controller_conn,
            ai_conn=self.ai_conn,
            queues=self.queues,
            processes=self.processes,
        )
