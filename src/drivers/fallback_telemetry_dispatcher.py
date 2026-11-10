# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Dispatches telemetry and incident payloads to fallback HTTP or MQTT endpoints.
Decouples transport fallback logic from IncidentReporter to respect SRP and Clean Architecture.
"""

import json
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class FallbackTelemetryDispatcher:
    """
    Handles dispatching telemetry payload directly to HTTP or MQTT endpoints
    when primary MonitorClient is unavailable or returns failure.
    """

    @staticmethod
    def dispatch(
        host_str: str,
        payload: Dict[str, Any],
        client_id: str = "carina_incident_reporter",
        intersection_id: str = "",
    ) -> bool:
        """
        Dispatches payload to host_str via HTTP or MQTT depending on endpoint format.
        Returns True if sent successfully, False otherwise.
        """
        level_str = str(payload.get("level", "INFO"))
        try:
            from communication.monitor_transport import is_http_endpoint, normalize_http_url

            if is_http_endpoint(host_str):
                import requests

                url = normalize_http_url(host_str)
                requests.post(url, json=payload, timeout=3.0)
                prefix = f"[{intersection_id}] " if intersection_id else ""
                logger.info(f"{prefix}Successfully emitted structured {level_str} to HTTP Monitor at {url}")
                return True
            else:
                from communication.monitor_transport import MonitorMqttTransport

                host, port = MonitorMqttTransport.parse_host_port(host_str)

                import paho.mqtt.client as mqtt

                client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
                client.connect(host, port, 60)
                client.loop_start()
                info = client.publish("noxfort/telemetry/", json.dumps(payload), qos=1)
                info.wait_for_publish(timeout=2.0)
                client.loop_stop()
                client.disconnect()
                prefix = f"[{intersection_id}] " if intersection_id else ""
                logger.info(
                    f"{prefix}Successfully emitted structured {level_str} to MQTT topic 'noxfort/telemetry/' at {host}:{port}"
                )
                return True
        except Exception as err:
            logger.warning(f"Fallback telemetry dispatch error to '{host_str}': {err}", exc_info=True)
            return False
