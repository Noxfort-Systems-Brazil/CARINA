# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import logging
import os
import threading
import time
from typing import Optional


class DemoXAIWorker:
    """Monitors simulated XAI filesystem requests and generates attribution responses."""

    @staticmethod
    def process_pending_requests(req_dir: str, res_dir: str) -> None:
        """Processes any .request files in req_dir and writes corresponding .response files."""
        if not os.path.exists(req_dir):
            return

        req_files = [f for f in os.listdir(req_dir) if f.endswith(".request")]
        for rf in req_files:
            aid = rf.replace(".request", "")
            req_path = os.path.join(req_dir, rf)
            logging.info(f"[DemoXAIWorker] Processing XAI request for agent {aid}...")
            time.sleep(1.2)
            try:
                from demo.mock_report_generator import generate_xai_plot_base64, generate_xai_text_report
                res_path = os.path.join(res_dir, f"{aid}.response")
                with open(res_path, "w", encoding="utf-8") as f:
                    json.dump({
                        "status": "complete",
                        "image_base64": generate_xai_plot_base64(aid),
                        "text_content": generate_xai_text_report(aid),
                    }, f)
                try:
                    os.remove(req_path)
                except Exception:
                    pass
                logging.info(f"[DemoXAIWorker] XAI response published for agent {aid}")
            except Exception as e:
                logging.error(f"[DemoXAIWorker] Error writing XAI response: {e}")

    @classmethod
    def run_loop(cls, is_running_cb, shutdown_event: threading.Event) -> None:
        """Polls requests directory periodically while active."""
        try:
            from src.utils.paths import get_base_output_dir
            base_dir = get_base_output_dir()
        except Exception:
            base_dir = "/home/gabriel-moraes/Documentos/Carina"

        req_dir = os.path.join(base_dir, "results", "hft_live_session", "captum", "requests")
        res_dir = os.path.join(base_dir, "results", "hft_live_session", "captum", "responses")

        while is_running_cb() and not shutdown_event.is_set():
            try:
                cls.process_pending_requests(req_dir, res_dir)
            except Exception:
                pass
            time.sleep(0.5)
