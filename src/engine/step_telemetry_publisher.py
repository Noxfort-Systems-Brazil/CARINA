# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import Any, Dict, Optional


class StepTelemetryPublisher:
    """
    Outbound IPC telemetry adapter responsible for packaging and sending
    real-time HFT simulation state updates across the central controller pipe.
    """

    def __init__(self, pipe_conn: Optional[Any] = None) -> None:
        self.pipe_conn = pipe_conn

    def set_pipe_conn(self, pipe_conn: Optional[Any]) -> None:
        """Updates the active IPC connection handle."""
        self.pipe_conn = pipe_conn

    def publish(
        self,
        sim_time: float,
        edges_data: Dict[str, Any],
        current_stages: Dict[str, Any],
        tls_lanes_state: Dict[str, Any],
        maturity_info: Dict[str, Any],
        mfd_data: Optional[Dict[str, Any]] = None,
        hardware_status: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Builds the rich HFT telemetry payload and dispatches it over the IPC channel.

        Returns:
            bool: True if dispatched successfully, False otherwise.
        """
        if not self.pipe_conn:
            return False

        rich_payload = {
            "edges": edges_data,
            "tls_phases": current_stages,
            "tls_lanes_state": tls_lanes_state,
            "maturity": maturity_info,
            "mfd": mfd_data,
            "sim_time": sim_time,
        }
        if hardware_status:
            rich_payload["hardware_status"] = hardware_status

        try:
            self.pipe_conn.send(("ai_telemetry_sync", rich_payload))
            return True
        except Exception as e:
            logging.error(f"[StepTelemetryPublisher] Failed to send AI Telemetry update: {e}", exc_info=True)
            return False
