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
# along with this program. If not, see <https://www.gnu.org/licenses/>.

# File: src/launcher/process_manager.py
# Author: Gabriel Moraes
# Date: August 6, 2026

import configparser
import logging
import os
import sys
import time
from multiprocessing import Pipe, Process, Queue

from central_controller import CentralController
from database.database_worker import run_database_worker
from launcher.process_reaper import ProcessReaper
from main import run_ai_process
from mfd.mfd_worker import run_mfd_worker
from sas.analysis_worker import run_analysis_worker
from sds.dashboard_worker import run_sds_worker
from utils.locale_manager_backend import LocaleManagerBackend
from utils.logging_setup import setup_logging
from utils.paths import get_base_output_dir, resource_path
from utils.process_monitor import ProcessMonitor
from watchdog.watchdog_process import run_watchdog
from xai.xai_worker import run_xai_worker

# Re-exports for backward compatibility
__all__ = ["ProcessManager", "run_controller_process", "ProcessReaper"]


def run_controller_process(settings, pipe_conn, wd_q, sds_q, sas_q, ui_q, mfd_trigger_q=None):
    """Target function for isolated execution of CentralController."""
    try:
        log_base_dir = get_base_output_dir()
        log_dir = os.path.join(log_base_dir, "logs", "central_controller")
        os.makedirs(log_dir, exist_ok=True)
        setup_logging(log_dir=log_dir)

        logging.info("[CentralController Process] Starting...")
        locale_manager = LocaleManagerBackend()

        # Start metrics & background process/GPU monitor
        ProcessMonitor.start_background_monitor(process_name="CentralController", port=8001)

        controller = CentralController(
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
        logging.error(f"[CentralController Process] Exception: {e}")
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

        # 2. AI Engine
        self.p_ai = Process(
            target=run_ai_process,
            args=(self.ai_conn, self.queues["g_state"], self.queues["g_signal"], self.queues["db"]),
            name="AI_Process",
        )
        self.processes.append(self.p_ai)

        # 3. Auxiliary Workers
        lm = LocaleManagerBackend()
        hft_results_dir = os.path.join(get_base_output_dir(), "results", "hft_live_session")
        os.makedirs(hft_results_dir, exist_ok=True)

        self.processes.append(Process(target=run_watchdog, args=(self.queues["wd"], lm), name="Watchdog"))
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
        logging.info("Starting XAI Worker...")
        self.processes.append(Process(target=run_xai_worker, args=(self.settings, hft_results_dir), name="XAI_Worker"))

        # 5. MFD Worker
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

        logging.info(f"All {len(self.processes)} BACKEND processes started. (Launcher PID: {os.getpid()})")

    def shutdown_all(self):
        """Delegates graceful shutdown and process tree cleanup to ProcessReaper."""
        ProcessReaper.shutdown_all(
            controller_conn=self.controller_conn,
            ai_conn=self.ai_conn,
            queues=self.queues,
            processes=self.processes,
        )
