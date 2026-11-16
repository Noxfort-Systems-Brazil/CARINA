# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import configparser
import logging
import os
import threading
import time
from multiprocessing import Queue

import psutil

from sds.dashboard_orchestrator import Orchestrator
from utils.locale_manager_backend import LocaleManagerBackend
from utils.logging_setup import setup_logging
from utils.metrics_manager import MetricsManager


def run_sds_worker(
    sds_data_queue: Queue,
    settings: configparser.ConfigParser,
    ui_command_queue: Queue,
    ui_telemetry_queue: Queue = None,
):
    """
    Entry point for the Simulation Data Service (SDS) process.
    """
    os.environ["CARINA_GATEWAY_ROLE"] = "remote"
    # --- CHANGE 1: Create translator instance for this process ---
    locale_manager = LocaleManagerBackend()
    lm = locale_manager

    def monitor_loop(metrics: MetricsManager, process: psutil.Process, queues: dict, interval: int = 5):
        while True:
            metrics.update_metric("process_cpu_usage_percent", process.cpu_percent())
            metrics.update_metric("process_memory_usage_percent", process.memory_percent())
            metrics.update_metric("sds_data_queue_size", queues["sds_data"].qsize())
            metrics.update_metric("ui_command_queue_size", queues["ui_command"].qsize())
            time.sleep(interval)

    metrics_manager = MetricsManager(process_name="DashboardService", port=8003)
    metrics_manager.register_metric("process_cpu_usage_percent", "Uso de CPU do processo (%)")
    metrics_manager.register_metric("process_memory_usage_percent", "Uso de Memória do processo (%)")
    metrics_manager.register_metric("sds_data_queue_size", "Tamanho da fila de dados da simulação para o SDS")
    metrics_manager.register_metric("ui_command_queue_size", "Tamanho da fila de comandos da UI para o Controller")

    current_process = psutil.Process()
    monitor_thread = threading.Thread(
        target=monitor_loop,
        args=(metrics_manager, current_process, {"sds_data": sds_data_queue, "ui_command": ui_command_queue}),
        daemon=True,
    )
    monitor_thread.start()

    try:
        from utils.paths import get_base_output_dir

        log_dir = os.path.join(get_base_output_dir(), "logs", "sds_worker")
        os.makedirs(log_dir, exist_ok=True)
        setup_logging(log_dir=log_dir)

        # --- CHANGE 2: Move the translator to Orchestrator ---
        orchestrator = Orchestrator(
            sds_data_queue, settings, ui_command_queue, locale_manager, ui_telemetry_queue=ui_telemetry_queue
        )

        # Runs the SDS orchestrator directly (telemetry decoupled from CCO)
        orchestrator.run()

    # --- CHANGE 3: Translate the exception and termination logs ---
    except KeyboardInterrupt:
        logging.info(lm.get_string("sds_worker.run.user_interrupt"))
    except Exception as e:
        logging.critical(lm.get_string("sds_worker.run.fatal_error", error=e), exc_info=True)
    finally:
        logging.info(lm.get_string("sds_worker.run.worker_finished"))
        os._exit(0)
