# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Publishes hardware incidents and connection state changes to MQTT.
Extracts monitoring and reporting concerns to satisfy SRP.
"""

import logging
from datetime import datetime
from typing import Any, Dict

from src.drivers.fallback_telemetry_dispatcher import FallbackTelemetryDispatcher

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
    """Logs incident reporter dispatch diagnostic details at debug level."""
    logger.debug(
        "[IncidentReporter] status=%s | id=%s | cat=%s | level=%s | active=%s | connected=%s | enabled=%s | msg=%s %s",
        status,
        intersection_id,
        category,
        level,
        is_active,
        mon_connected,
        mon_enabled,
        message_text,
        extra_info,
    )


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
                FallbackTelemetryDispatcher.dispatch(
                    host_str=host_str,
                    payload=payload,
                    client_id="carina_incident_reporter",
                    intersection_id=intersection_id,
                )
        except Exception as e:
            logger.error(f"[{intersection_id}] Failed to emit incident: {e}", exc_info=True)

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
                    FallbackTelemetryDispatcher.dispatch(
                        host_str=host_str,
                        payload=monitor_payload,
                        client_id="carina_trap_reporter",
                        intersection_id=intersection_id,
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
                        extra_info="Published via fallback MQTT",
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
            logger.error(f"[{intersection_id}] Failed to emit hardware trap to MQTT: {e}", exc_info=True)
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
