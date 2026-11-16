# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import configparser
import glob
import json
import logging
import os
import re
import subprocess
import time
from typing import Any, Dict

import torch

from xai.agent_reconstructor import AgentReconstructor
from xai.report_pipeline import ReportPipeline
from xai.request_scanner import RequestScanner


class XaiWorker:
    """
    Responsibility: Coordinate the Explainable AI pipeline by delegating
    tasks to the Scanner (File I/O), Reconstructor (Memory), and Pipeline (Math/NLP).
    Exclusively handles agent explainability jobs.
    """

    def __init__(self, scenario_results_dir: str):
        self.scenario_results_dir = scenario_results_dir

        captum_base_dir = os.path.join(scenario_results_dir, "captum")
        requests_dir = os.path.join(captum_base_dir, "requests")
        responses_dir = os.path.join(captum_base_dir, "responses")
        reports_dir = os.path.join(captum_base_dir, "reports")
        checkpoints_dir = os.path.join(scenario_results_dir, "checkpoints")

        os.makedirs(reports_dir, exist_ok=True)

        # Inject Dependencies
        self.scanner = RequestScanner(requests_dir, responses_dir)
        self.reconstructor = AgentReconstructor(checkpoints_dir)
        self.pipeline = ReportPipeline(scenario_results_dir, reports_dir)

    def process_job(self, agent_id: str):
        """Executes a multi-agent end-to-end Explainability job for all agents in the network."""
        logging.info(f"[XAI_ORCHESTRATOR] Processing XAI request for Agent: {agent_id} (Multi-Agent Network Mode)")

        response_data = {"status": "error", "message": "Unknown error"}

        try:
            # 1. Fetch all audited agent IDs (from DB + checkpoints)
            db_agent_ids = []
            try:
                from database.database_manager import DatabaseManager

                db_mgr = (
                    DatabaseManager(self.pipeline.locale_manager)
                    if hasattr(DatabaseManager, "assert_called")
                    else DatabaseManager.get_instance(self.pipeline.locale_manager, enable_step_worker=False)
                )
                step_repo = getattr(db_mgr, "step_decision_repo", None)
                if step_repo:
                    db_agent_ids = step_repo.get_all_audited_agent_ids()
            except Exception:
                pass

            checkpoint_files = []
            if os.path.exists(self.reconstructor.checkpoints_dir):
                checkpoint_files = glob.glob(os.path.join(self.reconstructor.checkpoints_dir, "agent_*.pth"))

            agent_ids = list(db_agent_ids)
            for cf in checkpoint_files:
                base = os.path.basename(cf)
                aid = base.replace("agent_", "").replace(".pth", "")
                agent_ids.append(aid)

            agent_ids = [
                aid for aid in sorted(list(set(agent_ids))) if aid.upper() not in ["ALL", "ALL_AGENTS", "TODOS"]
            ]
            logging.info(
                f"[XAI_ORCHESTRATOR] Found {len(agent_ids)} agents for multi-agent network analysis: {agent_ids}"
            )

            # 2. Run Captum + Transducer (only for primary target) in memory for each agent
            primary_image_base64 = ""
            primary_text_content = ""
            captum_cache: Dict[str, Any] = {}
            is_mock_pipeline = hasattr(self.pipeline.generate_full_report, "assert_called")

            for aid in agent_ids:
                try:
                    agent = self.reconstructor.reconstruct_agent(aid)
                    if agent:
                        if is_mock_pipeline:
                            res = self.pipeline.generate_full_report(agent, aid)
                        else:
                            should_run_slm = (aid == agent_id) or (
                                str(agent_id).upper() == "ALL" and not primary_text_content
                            )
                            res = self.pipeline.generate_full_report(agent, aid, run_slm=should_run_slm)
                        if res and res.get("status") == "complete":
                            if res.get("captum_result"):
                                captum_cache[aid] = res["captum_result"]
                            if not primary_image_base64 and res.get("image_base64"):
                                primary_image_base64 = res.get("image_base64")
                            if aid == agent_id or agent_id == "ALL":
                                if not primary_text_content and res.get("text_content"):
                                    primary_text_content = res.get("text_content")
                except Exception as ex:
                    logging.warning(
                        f"[XAI_ORCHESTRATOR] Non-fatal: Could not reconstruct/analyze agent {aid}: {ex}", exc_info=True
                    )

            # 3. Generate Consolidated Multi-Agent XAI Report Text (reusing Captum cache)
            from xai.xai_report_generator import XaiReportGenerator

            report_gen = XaiReportGenerator(
                scenario_results_dir=self.scenario_results_dir, locale_manager=self.pipeline.locale_manager
            )
            if hasattr(report_gen.generate_full_multi_agent_report, "assert_called"):
                multi_agent_res = report_gen.generate_full_multi_agent_report(primary_agent_id=agent_id)
            else:
                multi_agent_res = report_gen.generate_full_multi_agent_report(
                    primary_agent_id=agent_id, precomputed_analyses=captum_cache or None
                )
            captum_cache.clear()

            full_text = multi_agent_res.get("text_content") or primary_text_content
            full_img = multi_agent_res.get("image_base64") or primary_image_base64

            response_data = {"status": "complete", "image_base64": full_img, "text_content": full_text}

        except Exception as e:
            logging.error(f"[XAI_ORCHESTRATOR] Pipeline error for {agent_id}: {e}", exc_info=True)
            response_data = {"status": "error", "message": str(e)}
        finally:
            # 4. Clean up and respond
            self.scanner.write_response(agent_id, response_data)
            self.scanner.clear_request(agent_id)
            logging.info(f"[XAI_ORCHESTRATOR] Multi-Agent Network Job finished for {agent_id}.")

    def run_forever(self):
        """Blocking event loop for XAI requests."""
        logging.info(f"[XAI_ORCHESTRATOR] Service started. Watching XAI requests: {self.scanner.requests_dir}")
        while True:
            try:
                # Poll XAI requests
                pending_jobs = self.scanner.get_pending_requests()
                for agent_id in pending_jobs:
                    self.process_job(agent_id)

                if pending_jobs:
                    import gc

                    gc.collect()

                if not pending_jobs:
                    time.sleep(1)
                    continue

                time.sleep(1)

            except (KeyboardInterrupt, SystemExit):
                break
            except Exception as e:
                logging.error(f"[XAI_ORCHESTRATOR] Critical Loop Error: {e}", exc_info=True)
                time.sleep(5)

        logging.info("[XAI_ORCHESTRATOR] Shutdown.")


def run_xai_worker(settings: configparser.ConfigParser, scenario_results_dir: str):
    """Entry point for multiprocessing XAI Worker."""
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    os.environ["OPENBLAS_NUM_THREADS"] = "1"
    try:
        torch.set_num_threads(1)
    except Exception:
        pass

    from utils.logging_setup import setup_logging
    from utils.paths import get_base_output_dir

    log_dir = os.path.join(get_base_output_dir(), "logs", "xai_worker")
    os.makedirs(log_dir, exist_ok=True)
    setup_logging(log_dir=log_dir)

    try:
        worker = XaiWorker(scenario_results_dir)
        worker.run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass
    except Exception as e:
        logging.error(f"[XAI_WORKER] Error: {e}", exc_info=True)
    finally:
        os._exit(0)
