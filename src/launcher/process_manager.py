# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import configparser
import logging
import os
import sys
import threading
import time
from multiprocessing import Pipe, Process, Queue

from launcher.process_reaper import ProcessReaper
from utils.locale_manager_backend import LocaleManagerBackend
from utils.logging_setup import setup_logging
from utils.paths import get_base_output_dir, resource_path
from utils.process_monitor import ProcessMonitor

# Re-exports for backward compatibility
__all__ = ["ProcessManager", "run_controller_process", "ProcessReaper"]


def __getattr__(name: str):
    """Lazy resolver for legacy module-level worker attributes (PEP 562)."""
    if name == "CentralController":
        from central_controller import CentralController

        return CentralController
    if name == "run_ai_process":
        from main import run_ai_process

        return run_ai_process
    if name == "run_database_worker":
        from database.database_worker import run_database_worker

        return run_database_worker
    if name == "run_watchdog":
        from watchdog.watchdog_process import run_watchdog

        return run_watchdog
    if name == "run_sds_worker":
        from sds.dashboard_worker import run_sds_worker

        return run_sds_worker
    if name == "run_analysis_worker":
        from sas.analysis_worker import run_analysis_worker

        return run_analysis_worker
    if name == "run_xai_worker":
        from xai.xai_worker import run_xai_worker

        return run_xai_worker
    if name == "run_mfd_worker":
        from mfd.mfd_worker import run_mfd_worker

        return run_mfd_worker
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def run_controller_process(settings, pipe_conn, wd_q, sds_q, sas_q, ui_q, mfd_trigger_q=None):
    """Target function for isolated execution of CentralController."""
    try:
        from launcher.env_setup import setup_environment

        setup_environment()

        cc_cls = getattr(sys.modules[__name__], "CentralController")

        log_base_dir = get_base_output_dir()
        log_dir = os.path.join(log_base_dir, "logs", "central_controller")
        os.makedirs(log_dir, exist_ok=True)
        setup_logging(log_dir=log_dir)

        logging.info("[CentralController Process] Starting...")
        try:
            from utils.hardware_initializer import HardwareInitializer

            HardwareInitializer.setup_environment()
        except Exception:
            pass
        locale_manager = LocaleManagerBackend()

        # Start metrics & background process/GPU monitor
        ProcessMonitor.start_background_monitor(process_name="CentralController", port=8001)

        controller = cc_cls(
            settings,
            pipe_conn,
            wd_q,
            sds_q,
            sas_q,
            ui_q,
            locale_manager,
            mfd_trigger_queue=mfd_trigger_q,
        )
        controller.run()  # Blocks here on the gRPC server
    except (KeyboardInterrupt, SystemExit):
        pass
    except Exception as e:
        logging.error(f"[CentralController Process] Exception: {e}", exc_info=True)
    finally:
        os._exit(0)


class ProcessManager:
    """
    Manager responsible for creating IPC queues, loading configuration,
    instantiating CARINA backend processes, and coordinating shutdown.
    Delegates process tree walk, signal propagation, and zombie cleanup to ProcessReaper.
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
        self._fenix_supervision_thread = None
        self._stop_fenix_supervision = threading.Event()

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

        # 1. Central Controller
        self.p_cc = Process(
            target=run_controller_process,
            args=(
                self.settings,
                self.controller_conn,
                self.queues["wd"],
                self.queues["sds"],
                self.queues["sas"],
                self.queues["ui"],
                self.queues["mfd_trigger"],
            ),
            name="CentralController",
        )
        self.processes.append(self.p_cc)

        # 2. AI Engine with F.E.N.I.X. Supervision
        from main import run_ai_process
        from fenix.fenix_supervisor import FenixSupervisor
        from fenix.multiprocessing_runner import MultiprocessingProcessRunner

        ai_args = (self.ai_conn, self.queues["g_state"], self.queues["g_signal"], self.queues["db"])
        runner = MultiprocessingProcessRunner(target=run_ai_process, args=ai_args, name="AI_Process")
        self.fenix_supervisor = FenixSupervisor(runner=runner)

        self.p_ai = Process(
            target=run_ai_process,
            args=ai_args,
            name="AI_Process",
        )
        runner.set_process(self.p_ai)
        self.processes.append(self.p_ai)

        # 3. Auxiliary Workers
        from database.database_worker import run_database_worker
        from sas.analysis_worker import run_analysis_worker
        from sds.dashboard_worker import run_sds_worker
        from watchdog.watchdog_process import run_watchdog

        lm = LocaleManagerBackend()
        hft_results_dir = os.path.join(get_base_output_dir(), "results", "hft_live_session")
        os.makedirs(hft_results_dir, exist_ok=True)

        self.processes.append(
            Process(target=run_watchdog, args=(self.queues["wd"], lm, self.queues["fenix"]), name="Watchdog")
        )
        self.processes.append(
            Process(
                target=run_sds_worker,
                args=(self.queues["sds"], self.settings, self.queues["ui"], self.queues["ui_telemetry"]),
                name="DashboardService",
            )
        )
        self.processes.append(
            Process(
                target=run_analysis_worker,
                args=(self.queues["sas"], self.settings, self.queues["db"], self.queues["sas_results"]),
                name="AnalysisService",
            )
        )
        self.processes.append(Process(target=run_database_worker, args=(self.queues["db"],), name="DatabaseWorker"))

        # 4. XAI Worker
        from xai.xai_worker import run_xai_worker

        logging.info("Starting XAI Worker...")
        self.processes.append(Process(target=run_xai_worker, args=(self.settings, hft_results_dir), name="XAI_Worker"))

        # 5. MFD Worker
        from mfd.mfd_worker import run_mfd_worker

        logging.info("Starting MFD Worker...")
        self.processes.append(
            Process(
                target=run_mfd_worker,
                args=(self.settings, hft_results_dir, self.queues["mfd_results"], self.queues["mfd_trigger"]),
                name="MFD_Worker",
            )
        )

        for p in self.processes:
            p.start()
            logging.info(f" -> Process [{p.name}] successfully started! PID: {p.pid}")
            time.sleep(0.3)

        self._start_fenix_supervision()

        logging.info(f"All {len(self.processes)} BACKEND processes started. (Launcher PID: {os.getpid()})")

    def _start_fenix_supervision(self):
        """Starts background supervisor thread listening for FENIX recovery triggers."""
        if not self.fenix_supervisor:
            return
        self._stop_fenix_supervision.clear()
        self._fenix_supervision_thread = threading.Thread(
            target=self._fenix_supervision_loop,
            name="FenixSupervisionThread",
            daemon=True,
        )
        self._fenix_supervision_thread.start()
        logging.info("[ProcessManager] F.E.N.I.X. background supervision thread active.")

    def _fenix_supervision_loop(self):
        """Listens on fenix IPC queue and handles resurrection requests."""
        fenix_q = self.queues.get("fenix")
        if not fenix_q:
            return

        import queue

        while not self._stop_fenix_supervision.is_set():
            try:
                msg = fenix_q.get(timeout=0.5)
            except queue.Empty:
                continue
            except Exception as e:
                logging.debug(f"[ProcessManager] Error reading fenix_q: {e}")
                continue

            if msg == "STOP" or self._stop_fenix_supervision.is_set():
                break

            action = msg[0] if isinstance(msg, tuple) else msg
            reason = msg[1] if isinstance(msg, tuple) and len(msg) > 1 else "Unknown"

            if action in ("TRIGGER_RESURRECTION", "CRASH_TRIGGER"):
                logging.critical(
                    f"[ProcessManager] 🚨 F.E.N.I.X. resurrection triggered (Reason: {reason}). "
                    "Executing AI Engine resurrection..."
                )
                if self.fenix_supervisor:
                    self.fenix_supervisor.record_child_crash(exit_code=1)
                    resurrected = self.fenix_supervisor.resurrect_ai()
                    if resurrected and hasattr(self.fenix_supervisor.runner, "_process"):
                        new_proc = self.fenix_supervisor.runner._process
                        if new_proc:
                            self.p_ai = new_proc
                            for idx, p in enumerate(self.processes):
                                if p.name == "AI_Process":
                                    self.processes[idx] = new_proc
                                    break
                            logging.info(
                                f"[ProcessManager] ✅ F.E.N.I.X. AI Process successfully resurrected! [New PID: {new_proc.pid}]"
                            )
                    else:
                        logging.error(
                            f"[ProcessManager] ❌ F.E.N.I.X. resurrection halted or failed. Supervisor state: {self.fenix_supervisor.state.value}"
                        )

    def shutdown_all(self):
        """Delegates graceful shutdown and process tree cleanup to ProcessReaper."""
        self._stop_fenix_supervision.set()
        fenix_q = self.queues.get("fenix")
        if fenix_q:
            try:
                fenix_q.put_nowait("STOP")
            except Exception:
                pass

        if self._fenix_supervision_thread and self._fenix_supervision_thread.is_alive():
            self._fenix_supervision_thread.join(timeout=1.0)

        if getattr(self, "fenix_supervisor", None):
            try:
                self.fenix_supervisor.stop()
            except Exception:
                pass

        ProcessReaper.shutdown_all(
            controller_conn=self.controller_conn,
            ai_conn=self.ai_conn,
            queues=self.queues,
            processes=self.processes,
        )
