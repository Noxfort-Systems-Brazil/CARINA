# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import configparser
import logging
import os
import queue
import time

from mfd.mfd_processor import MFDHistoryReconstructor
from mfd.mfd_report_generator import MFDReportGenerator


class MFDOrchestrator:
    """
    Responsibility: Dedicated orchestrator for Macroscopic Fundamental Diagram (MFD)
    Optimization Analysis. Processes MFD reports via 100% in-memory IPC queue (mfd_result_queue).
    """

    def __init__(
        self, scenario_results_dir: str, mfd_reconstructor=None, mfd_result_queue=None, mfd_trigger_queue=None
    ):
        self.scenario_results_dir = scenario_results_dir
        self.mfd_result_queue = mfd_result_queue
        self.mfd_trigger_queue = mfd_trigger_queue
        self.mfd_reconstructor = mfd_reconstructor or MFDHistoryReconstructor(scenario_results_dir)

    def process_mfd_job(self, req_id: str = "mfd"):
        """Executes a single end-to-end MFD Optimization Analysis job and delivers result to in-memory IPC queue."""
        logging.info(f"[MFD_ORCHESTRATOR] Processing in-memory MFD Optimization request: {req_id}")

        response_data = {"status": "error", "message": "Unknown error"}

        try:
            mfd_history_data = self.mfd_reconstructor.reconstruct_from_db()
            if not mfd_history_data or not mfd_history_data.get("history"):
                raise ValueError(
                    "Nenhum registro histórico de tráfego foi encontrado no banco de dados (tabelas synapse_fluid_dynamics / synapse_edge_phase_hourly_summary). É necessário haver amostras no banco de dados para gerar a análise."
                )
            response_data = self.generate_mfd_report(mfd_history_data)

        except Exception as e:
            logging.error(f"[MFD_ORCHESTRATOR] MFD pipeline error for {req_id}: {e}", exc_info=True)
            response_data = {"status": "error", "message": str(e)}
        finally:
            response_data["timestamp"] = time.time()
            if self.mfd_result_queue is not None:
                self.mfd_result_queue.put(response_data)
                logging.info(f"[MFD_ORCHESTRATOR] MFD job result delivered to in-memory IPC queue: {req_id}.")
            else:
                logging.warning("[MFD_ORCHESTRATOR] MFD job finished but mfd_result_queue is NULL.")

    def generate_mfd_report(self, mfd_history_data: dict) -> dict:
        return MFDReportGenerator.generate_report(mfd_history_data, scenario_results_dir=self.scenario_results_dir)

    def run_forever(self):
        """Blocking event loop for MFD trigger requests."""
        logging.info("[MFD_ORCHESTRATOR] MFD Worker Service started. Listening for MFD trigger packets...")
        while True:
            try:
                if self.mfd_trigger_queue and not self.mfd_trigger_queue.empty():
                    try:
                        msg = self.mfd_trigger_queue.get_nowait()
                        if msg is None or msg == "STOP":
                            logging.info("[MFD_ORCHESTRATOR] Stop signal received. Exiting MFD Worker.")
                            break
                        logging.info(
                            "[MFD_ORCHESTRATOR] In-memory MFD trigger packet received! Starting process_mfd_job()..."
                        )
                        self.process_mfd_job()
                    except Exception as trig_err:
                        logging.error(f"[MFD_ORCHESTRATOR] Error processing MFD trigger packet: {trig_err}", exc_info=True)

                time.sleep(1)
            except (KeyboardInterrupt, SystemExit):
                break
            except Exception as e:
                logging.error(f"[MFD_ORCHESTRATOR] Critical Loop Error: {e}", exc_info=True)
                time.sleep(5)

        logging.info("[MFD_ORCHESTRATOR] Shutdown.")


def run_mfd_worker(
    settings: configparser.ConfigParser, scenario_results_dir: str, mfd_result_queue=None, mfd_trigger_queue=None
):
    """Entry point for multiprocessing MFD Worker."""

    from utils.logging_setup import setup_logging
    from utils.paths import get_base_output_dir

    log_dir = os.path.join(get_base_output_dir(), "logs", "mfd_worker")
    os.makedirs(log_dir, exist_ok=True)
    setup_logging(log_dir=log_dir)

    try:
        orchestrator = MFDOrchestrator(
            scenario_results_dir, mfd_result_queue=mfd_result_queue, mfd_trigger_queue=mfd_trigger_queue
        )
        orchestrator.run_forever()
    except (KeyboardInterrupt, SystemExit):
        logging.info("[MFD_WORKER] Terminated via interrupt/exit signal.")
    except Exception as e:
        logging.error(f"[MFD_WORKER] Error: {e}", exc_info=True)
    finally:
        os._exit(0)
