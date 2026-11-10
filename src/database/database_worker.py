# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import os
import threading
import time
from multiprocessing import Queue

import psutil

from database.database_manager import DatabaseManager
from utils.locale_manager_backend import LocaleManagerBackend
from utils.logging_setup import setup_logging
from utils.metrics_manager import MetricsManager


def run_database_worker(db_queue: Queue):
    """
    Entry point for the Database Worker process.
    """
    # --- FIX APPLIED HERE: Boot order has been reversed ---

    # 1. Configure FIRST logging.
    from utils.paths import get_base_output_dir

    log_dir = os.path.join(get_base_output_dir(), "logs", "db_worker")
    os.makedirs(log_dir, exist_ok=True)
    setup_logging(log_dir=log_dir)

    # 2. With logging active, create the LocaleManager AFTER.
    lm = LocaleManagerBackend()

    # --- END OF CORRECTION ---

    from database.worker_monitor import WorkerMonitor

    monitor = WorkerMonitor(process_name="DatabaseWorker", port=8005, monitered_queues={"db_data": db_queue})

    monitor_thread = threading.Thread(target=monitor.start_loop, args=(5,), daemon=True)
    monitor_thread.start()

    try:
        # setup_logging has already been moved to the top

        db_manager = DatabaseManager(locale_manager=lm, run_migrations=True)

        def cloud_sync_loop(db_mgr, base_dir):
            # Give the system some time to boot before first sync
            time.sleep(30)
            while True:
                try:
                    db_mgr.sync_all_files_to_vault(base_dir)
                except Exception as e:
                    logging.error(f"[CLOUD_SYNC] Error in sync loop: {e}", exc_info=True)
                # Wait 5 minutes before next sync
                time.sleep(300)

        cloud_sync_thread = threading.Thread(
            target=cloud_sync_loop, args=(db_manager, get_base_output_dir()), daemon=True
        )
        cloud_sync_thread.start()

        def consolidation_purge_loop(db_mgr):
            # Wait 15 seconds before initial consolidation on boot
            time.sleep(15)
            while True:
                try:
                    db_mgr.consolidate_and_purge_old_data(keep_hours=48)
                except Exception as e:
                    logging.error(f"[DB_WORKER] Error in consolidation purge loop: {e}", exc_info=True)
                # Run consolidation every 1 hour (3600 seconds)
                time.sleep(3600)

        consolidation_purge_thread = threading.Thread(target=consolidation_purge_loop, args=(db_manager,), daemon=True)
        consolidation_purge_thread.start()

        logging.info(lm.get_string("db_worker.run.worker_started"))

        while True:
            data_packet = db_queue.get()

            if data_packet is None:
                logging.info(lm.get_string("db_worker.run.shutdown_signal"))
                break

            try:
                log_type = data_packet.get("type")
                payload = data_packet.get("payload", {})

                if log_type == "log_episode":
                    db_manager.log_episode(**payload)
                elif log_type == "log_report":
                    db_manager.log_analysis_report(**payload)
                elif log_type == "sync_files":
                    db_manager.sync_all_files_to_vault(get_base_output_dir())
                elif log_type == "consolidate_purge":
                    keep_hours = payload.get("keep_hours", 48)
                    db_manager.consolidate_and_purge_old_data(keep_hours=keep_hours)
                else:
                    logging.warning(lm.get_string("db_worker.run.unknown_log_type", type=log_type))

            except Exception as e:
                logging.error(lm.get_string("db_worker.run.processing_error", packet=data_packet), exc_info=e)

    except KeyboardInterrupt:
        logging.info(lm.get_string("db_worker.run.user_interrupt"))
    except Exception as e:
        logging.critical(lm.get_string("db_worker.run.fatal_error", error=e), exc_info=True)
    finally:
        logging.info(lm.get_string("db_worker.run.worker_finished"))
        os._exit(0)
