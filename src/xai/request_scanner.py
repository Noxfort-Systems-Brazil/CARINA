# File: src/xai/request_scanner.py
# Author: Gabriel Moraes
# Date: December 17, 2025

import os
import time
import logging
import json
from typing import List, Optional

class RequestScanner:
    """
    Responsibility: Scan the requests directory for incoming XAI jobs,
    parse the agent IDs, and provide a clean API to retrieve and manage them.
    """

    def __init__(self, requests_dir: str, responses_dir: str):
        self.requests_dir = requests_dir
        self.responses_dir = responses_dir
        os.makedirs(self.requests_dir, exist_ok=True)
        os.makedirs(self.responses_dir, exist_ok=True)

    def get_pending_requests(self) -> List[str]:
        """Scans the directory and returns a list of pending Agent IDs."""
        if not os.path.exists(self.requests_dir):
            return []

        try:
            files = [f for f in os.listdir(self.requests_dir) if f.endswith(".request")]
            return [f.replace(".request", "") for f in files]
        except Exception as e:
            logging.error(f"[RequestScanner] Error scanning directory: {e}")
            return []

    def clear_request(self, agent_id: str):
        """Removes the request file after processing."""
        request_path = os.path.join(self.requests_dir, f"{agent_id}.request")
        if os.path.exists(request_path):
            try:
                os.remove(request_path)
            except OSError as e:
                logging.error(f"[RequestScanner] Error removing request file {request_path}: {e}")

    def write_response(self, agent_id: str, response_data: dict) -> bool:
        """Writes the final output payload back to the response directory atomically."""
        response_path = os.path.join(self.responses_dir, f"{agent_id}.response")
        response_tmp_path = response_path + ".tmp"
        
        try:
            with open(response_tmp_path, "w", encoding="utf-8") as f:
                json.dump(response_data, f, indent=4)
            os.rename(response_tmp_path, response_path)
            return True
        except Exception as e:
            logging.error(f"[RequestScanner] Failed to write response for {agent_id}: {e}")
            return False
