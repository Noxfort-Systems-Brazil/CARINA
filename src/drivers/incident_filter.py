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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# File: src/drivers/incident_filter.py
# Author: Gabriel Moraes
# Date: 2026-07-31

"""
Incident Filter Intermediary Module.
Filters duplicate hardware alert bursts before forwarding incidents to IncidentReporter,
supporting cross-process deduplication.
"""

import logging
import os
import tempfile
import threading
import time
from typing import Any, Dict

from src.drivers.incident_reporter import IncidentReporter

logger = logging.getLogger(__name__)


def _log_filter_debug(intersection_id: str, message_text: str, is_duplicate: bool, action: str) -> None:
    """Disabled temporary debug logging."""
    pass


class IncidentFilter:
    """
    Intermediary filter component for Monitor incident reporting.
    Uses in-memory cache and OS temp file stamp for cross-process deduplication.
    """

    _lock = threading.Lock()
    _last_key: str = ""
    _last_time: float = 0.0

    @staticmethod
    def process_and_report(intersection_id: str, level: str, trap_data: Dict[str, Any]) -> None:
        """
        Processes incoming trap data using cross-process and in-memory deduplication.
        If ID and Message Text match the last sent message within 1.0s across any process, it is silently dropped.
        """
        try:
            resolved_id = str(trap_data.get("intersection_id", intersection_id))
            details = trap_data.get("details") or trap_data.get("message") or "Alerta ativo de hardware recebido"

            if trap_data.get("message"):
                msg_text = str(trap_data.get("message"))
            elif resolved_id and resolved_id != "DESCONHECIDO":
                msg_text = f"[{resolved_id}] {details}"
            else:
                msg_text = str(details)

            current_key = f"{resolved_id}:{msg_text}"
            now = time.time()

            stamp_file = os.path.join(tempfile.gettempdir(), ".carina_incident_filter.stamp")

            time_diff = 999.0
            with IncidentFilter._lock:
                if IncidentFilter._last_key == current_key:
                    time_diff = now - IncidentFilter._last_time

            if os.path.exists(stamp_file):
                try:
                    with open(stamp_file, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        if content and "|||" in content:
                            parts = content.split("|||")
                            if len(parts) == 2:
                                last_key, last_time_str = parts[0], float(parts[1])
                                if last_key == current_key:
                                    file_time_diff = now - last_time_str
                                    time_diff = min(time_diff, file_time_diff)
                except Exception:
                    pass

            # Cross-process comparison: if identical message arrived < 1.0s ago anywhere -> DUPLICATE!
            if time_diff < 1.0:
                _log_filter_debug(
                    resolved_id, msg_text, True, f"DROPPED (DUPLICATE BURST IGNORED - diff: {time_diff:.4f}s)"
                )
                logger.info(f"[IncidentFilter] Ignored duplicate cross-process burst ({time_diff:.4f}s): {msg_text}")
                return

            with IncidentFilter._lock:
                IncidentFilter._last_key = current_key
                IncidentFilter._last_time = now

            # Write current key and timestamp to shared cross-process file stamp in system temp dir
            try:
                with open(stamp_file, "w", encoding="utf-8") as f:
                    f.write(f"{current_key}|||{now}")
            except Exception:
                pass

            _log_filter_debug(resolved_id, msg_text, False, f"FORWARDED TO INCIDENT_REPORTER (diff: {time_diff:.4f}s)")
            IncidentReporter.report_trap(intersection_id, level, trap_data)
        except Exception as err:
            logger.error(f"[IncidentFilter] Error in incident filter: {err}")
