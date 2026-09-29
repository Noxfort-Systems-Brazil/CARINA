# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Noxfort Systems
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

# File: src/drivers/incident_reporter.py
# Author: Gabriel Moraes
# Date: 2026-06-16

"""
Publishes hardware incidents and connection state changes to MQTT.
Extracts monitoring and reporting concerns to satisfy SRP.
"""

import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict

logger = logging.getLogger(__name__)


def _log_incident_reporter_debug(
    status: str,
    intersection_id: str,
    category: str,
    level: str,
    message_text: str,
    is_active: bool,
    mon_connected: bool,
    mon_enabled: bool,
    extra_info: str = "",
):
    """Disabled temporary debug logging."""
    pass


class IncidentReporter:
    """
    Handles publishing traffic signal events and incidents to external systems (e.g. MQTT).
    """

    @staticmethod
    def report(intersection_id: str, level: str, message: str) -> None:
        """Publishes an incident to the Monitor MQTT topic dynamically if enabled."""
        try:
            from src.communication.monitor_client import MonitorClient
            from src.utils.settings_manager import SettingsManager

            settings = SettingsManager().load_settings()
            is_enabled_in_settings = str(settings.get("monitor_enabled", "False")).strip().lower() in (
                "true",
                "1",
                "yes",
                "on",
            )
            if not is_enabled_in_settings:
                # Monitor is administratively disabled. Do not contact or attempt reconnection.
                return

            mon_client = MonitorClient.get_instance(SettingsManager())
            if not mon_client or not mon_client.enabled:
                return

            mon_conn = mon_client._ensure_connected()
            if not mon_conn:
                return

            cat = "HARDWARE" if "HARDWARE" in str(message).upper() else "SOFTWARE"
            msg_text = (
                f"[{intersection_id}] {message}"
                if intersection_id and intersection_id != "DESCONHECIDO" and not str(message).startswith("[")
                else str(message)
            )
            success = mon_client.report_incident(category=cat, level=level, message=msg_text)
            if not success:
                host_str = settings.get("monitor_mqtt_host", "localhost")
                payload = {
                    "category": cat,
                    "origin": "Carina",
                    "level": str(level).upper(),
                    "message": msg_text,
                    "occurred_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                }

                try:
                    from communication.monitor_transport import is_http_endpoint, normalize_http_url
                except Exception:
                    from src.communication.monitor_transport import is_http_endpoint, normalize_http_url

                if is_http_endpoint(host_str):
                    import requests

                    url = normalize_http_url(host_str)
                    requests.post(url, json=payload, timeout=3.0)
                else:
                    try:
                        from communication.monitor_transport import MonitorMqttTransport
                    except Exception:
                        from src.communication.monitor_transport import MonitorMqttTransport
                    host, port = MonitorMqttTransport.parse_host_port(host_str)

                    try:
                        import paho.mqtt.client as mqtt

                        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="carina_incident_reporter")
                        client.connect(host, port, 60)
                        client.loop_start()
                        info = client.publish("noxfort/telemetry/", json.dumps(payload), qos=1)
                        info.wait_for_publish(timeout=2.0)
                        client.loop_stop()
                        client.disconnect()
                    except Exception as mqtt_err:
                        logger.warning(f"Fallback MQTT dispatch error: {mqtt_err}")
        except Exception as e:
            logger.error(f"[{intersection_id}] Failed to emit incident: {e}")

    @staticmethod
    def report_trap(intersection_id: str, level: str, trap_data: dict) -> None:
        """Publishes a structured active hardware trap payload to the Monitor MQTT topic dynamically if enabled."""
        try:
            from src.communication.monitor_client import MonitorClient
            from src.utils.settings_manager import SettingsManager

            settings = SettingsManager().load_settings()
            is_enabled_in_settings = str(settings.get("monitor_enabled", "False")).strip().lower() in (
                "true",
                "1",
                "yes",
                "on",
            )
            if not is_enabled_in_settings:
                # Monitor is administratively disabled. Do not contact or attempt reconnection.
                return

            category = trap_data.get("category", "HARDWARE")
            level_str = trap_data.get("level", "CRITICAL")

            details = trap_data.get("details") or trap_data.get("message") or "Alerta ativo de hardware recebido"
            resolved_id = trap_data.get("intersection_id", intersection_id)

            if trap_data.get("message"):
                message_text = str(trap_data.get("message"))
            elif resolved_id and resolved_id != "DESCONHECIDO":
                message_text = f"[{resolved_id}] {details}"
            else:
                message_text = str(details)

            logger.info(f"[{intersection_id}] Processing hardware trap for Monitor: {message_text}")

            mon_client = MonitorClient.get_instance(SettingsManager())
            mon_conn = False
            mon_en = False
            if mon_client:
                mon_en = getattr(mon_client, "enabled", False)
                if mon_en and hasattr(mon_client, "_ensure_connected"):
                    mon_conn = mon_client._ensure_connected()

            is_active = is_enabled_in_settings

            _log_incident_reporter_debug(
                status="REPORT_TRAP CALLED",
                intersection_id=resolved_id,
                category=category,
                level=level_str,
                message_text=message_text,
                is_active=is_active,
                mon_connected=mon_conn,
                mon_enabled=mon_en,
                extra_info=f"monitor_enabled setting: {settings.get('monitor_enabled')}",
            )

            if is_active:
                success = False
                if mon_client and mon_en and mon_conn:
                    success = mon_client.report_incident(category=category, level=level_str, message=message_text)
                    if success:
                        logger.info(
                            f"[{intersection_id}] Emitted {level_str} trap to Monitor via active MonitorClient."
                        )
                        _log_incident_reporter_debug(
                            status="EMITTED VIA MonitorClient SUCCESS",
                            intersection_id=resolved_id,
                            category=category,
                            level=level_str,
                            message_text=message_text,
                            is_active=is_active,
                            mon_connected=mon_conn,
                            mon_enabled=mon_en,
                            extra_info="Published via active MonitorClient",
                        )

                if not success:
                    host_str = settings.get("monitor_mqtt_host", "localhost")
                    monitor_payload = {
                        "category": category,
                        "origin": "Carina",
                        "level": level_str,
                        "message": message_text,
                        "occurred_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                    }

                    try:
                        from communication.monitor_transport import is_http_endpoint, normalize_http_url
                    except Exception:
                        from src.communication.monitor_transport import is_http_endpoint, normalize_http_url

                    if is_http_endpoint(host_str):
                        import requests

                        url = normalize_http_url(host_str)
                        requests.post(url, json=monitor_payload, timeout=3.0)
                        logger.info(
                            f"[{intersection_id}] Successfully emitted structured {level_str} hardware trap to HTTP Monitor at {url}"
                        )
                    else:
                        try:
                            from communication.monitor_transport import MonitorMqttTransport
                        except Exception:
                            from src.communication.monitor_transport import MonitorMqttTransport
                        host, port = MonitorMqttTransport.parse_host_port(host_str)

                        import paho.mqtt.client as mqtt

                        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="carina_trap_reporter")
                        client.connect(host, port, 60)
                        client.loop_start()
                        info = client.publish("noxfort/telemetry/", json.dumps(monitor_payload), qos=1)
                        info.wait_for_publish(timeout=2.0)
                        client.loop_stop()
                        client.disconnect()
                        logger.info(
                            f"[{intersection_id}] Successfully emitted structured {level_str} hardware trap to MQTT topic 'noxfort/telemetry/' at {host}:{port}"
                        )

                    _log_incident_reporter_debug(
                        status="EMITTED VIA FALLBACK MQTT SUCCESS",
                        intersection_id=resolved_id,
                        category=category,
                        level=level_str,
                        message_text=message_text,
                        is_active=is_active,
                        mon_connected=mon_conn,
                        mon_enabled=mon_en,
                        extra_info=f"Published via fallback MQTT to {host}:{port} topic 'noxfort/telemetry/'",
                    )
            else:
                logger.info(
                    f"[{intersection_id}] MQTT monitor disabled or inactive (monitor_enabled=False). Trap logged locally."
                )
                _log_incident_reporter_debug(
                    status="SKIPPED (IS_ACTIVE = FALSE)",
                    intersection_id=resolved_id,
                    category=category,
                    level=level_str,
                    message_text=message_text,
                    is_active=is_active,
                    mon_connected=mon_conn,
                    mon_enabled=mon_en,
                    extra_info="Skipped publishing because is_active is False",
                )
        except Exception as e:
            logger.error(f"[{intersection_id}] Failed to emit hardware trap to MQTT: {e}")
            _log_incident_reporter_debug(
                status="EXCEPTION ERROR",
                intersection_id=intersection_id,
                category="ERROR",
                level="ERROR",
                message_text=str(e),
                is_active=False,
                mon_connected=False,
                mon_enabled=False,
                extra_info=f"Exception in report_trap: {e}",
            )
