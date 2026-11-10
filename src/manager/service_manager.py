# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import configparser
import logging
import os
from multiprocessing import Process, Queue
from typing import TYPE_CHECKING

# --- CHANGE 1: Add required imports ---
if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

# Imports the entry point functions of each worker/service
from safety.guardian_worker import run_guardian_worker
from xai.xai_worker import run_xai_worker


class ServiceManager:
    """Manages the startup and shutdown of service processes."""

    # --- CHANGE 2: Modify the constructor ---
    def __init__(self, locale_manager: "LocaleManagerBackend"):
        """Initializes the service manager."""
        self.locale_manager = locale_manager
        self.guardian_worker_process: Process | None = None
        self.xai_worker_process: Process | None = None
        # --- CHANGE 3 ---
        logging.info(self.locale_manager.get_string("service_manager.init.created"))

    def start_all_services(
        self,
        settings: configparser.ConfigParser,
        guardian_state_queue: Queue,
        guardian_signal_queue: Queue,
        scenario_dir: str,
        agent_ids: list,
    ):
        """
        Starts all service processes in the background.
        """
        lm = self.locale_manager
        # --- CHANGE 4 ---
        logging.info(lm.get_string("service_manager.start.all"))

        self.guardian_worker_process = Process(
            target=run_guardian_worker,
            args=(settings, guardian_state_queue, guardian_signal_queue, scenario_dir, agent_ids),
            name="GuardianWorker",
        )
        self.guardian_worker_process.daemon = True
        self.guardian_worker_process.start()
        # --- CHANGE 5 ---
        logging.info(lm.get_string("service_manager.start.guardian_success", pid=self.guardian_worker_process.pid))

        self.xai_worker_process = Process(target=run_xai_worker, args=(settings, scenario_dir), name="XaiWorker")
        self.xai_worker_process.daemon = True
        self.xai_worker_process.start()
        # --- CHANGE 6 ---
        logging.info(lm.get_string("service_manager.start.xai_success", pid=self.xai_worker_process.pid))

    def stop_all_services(self):
        """
        Shuts down all service processes gracefully.
        """
        lm = self.locale_manager
        # --- CHANGE 7 ---
        logging.info(lm.get_string("service_manager.stop.all"))

        processes = {"Guardião Worker": self.guardian_worker_process, "XAI Worker": self.xai_worker_process}

        for name, process in processes.items():
            if process and process.is_alive():
                # --- CHANGE 8 ---
                logging.info(lm.get_string("service_manager.stop.terminating_process", name=name, pid=process.pid))
                process.terminate()
                process.join(timeout=5)
                if process.is_alive():
                    # --- CHANGE 9 ---
                    logging.warning(lm.get_string("service_manager.stop.force_kill", name=name))
                    process.kill()

        # --- CHANGE 10 ---
        logging.info(lm.get_string("service_manager.stop.all_finished"))
