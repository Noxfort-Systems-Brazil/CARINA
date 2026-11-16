# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Factory module for traffic light drivers.
Connects physical intersections via the compiled Go Hardware Gateway over OS standard pipes.
"""

import logging
import os
import re
from typing import Any, Dict, Optional

from src.drivers.base_driver import BaseTrafficDriver
from src.drivers.go_driver_proxy import GoTrafficDriverProxy
from src.drivers.go_gateway_client import GoGatewayClient
from src.utils.paths import resource_path

logger = logging.getLogger(__name__)


class DriverFactory:
    """
    Factory class responsible for instantiating the Go Hardware Gateway proxy
    and connecting intersections to their physical controllers.
    """

    @staticmethod
    def create_and_connect_driver(
        ip_address: str,
        port: int,
        community_string: str = "public",
        intersection_id: str = "Desconhecido",
        green_stages: list = None,
        locale_manager: Optional[Any] = None,
        snmp_config: Optional[Dict[str, Any]] = None,
        config_path: Optional[str] = None,
    ) -> Optional[BaseTrafficDriver]:
        """
        Connects target intersection to the Go Hardware Gateway.
        The Go gateway autonomously executes discovery, brand/model parsing,
        loads the appropriate JSON OIDs, and starts watchdog heartbeats.
        """

        def _get_string(key: str, default: str = None, **kwargs) -> str:
            if locale_manager and hasattr(locale_manager, "get_string"):
                return locale_manager.get_string(key, default=default, **kwargs)
            return default.format(**kwargs) if default and kwargs else (default or key)

        logger.info(f"[{ip_address}:{port}] Connecting intersection {intersection_id} via Go Hardware Gateway...")

        try:
            go_binary = resource_path(os.path.join("bin", "carina-go"))
            client = GoGatewayClient.get_instance(go_binary)
            if not client.is_running():
                client.start()

            connect_kwargs: Dict[str, Any] = {
                "intersection_id": intersection_id,
                "ip": ip_address,
                "port": port,
                "community": community_string,
                "protocol": "auto",
                "green_stages": green_stages,
            }
            resolved_cfg_path = config_path
            if not resolved_cfg_path and isinstance(snmp_config, dict):
                resolved_cfg_path = snmp_config.get("config_path") or snmp_config.get("oid_config_path")
            if resolved_cfg_path:
                connect_kwargs["config_path"] = str(resolved_cfg_path)
            if snmp_config:
                connect_kwargs["snmp_config"] = snmp_config

            res = client.connect_intersection(**connect_kwargs)

            if res.get("success", False):
                data = res.get("data", {})
                proto_name = data.get("protocol", "NTCIP 1202")
                detected_brand = data.get("brand", "Não informado")
                detected_model = data.get("model", "Não informado")

                logger.info(
                    f"[{ip_address}:{port}] Successfully connected intersection {intersection_id} "
                    f"({proto_name} - {detected_brand}/{detected_model})"
                )
                return GoTrafficDriverProxy(
                    ip_address=ip_address,
                    port=port,
                    intersection_id=intersection_id,
                    community_string=community_string,
                    green_stages=green_stages,
                    protocol_name=proto_name,
                    brand=detected_brand,
                    model=detected_model,
                    client=client,
                )
            else:
                err_msg = res.get("error", "Unknown error")
                logger.error(
                    _get_string(
                        "drivers.factory.connect_failed",
                        default="[{ip}:{port}] Failed to connect via Go Gateway: {error}",
                        ip=ip_address,
                        port=port,
                        error=err_msg,
                    )
                )
                return None

        except Exception as e:
            logger.error(
                f"[DriverFactory] Exception connecting to Go Gateway for [{ip_address}:{port}]: {e}", exc_info=True
            )
            return None

    @staticmethod
    def extract_brand_and_model(descr_val: Any) -> tuple[str, str]:
        """
        Parses sysDescr string to identify brand (manufacturer) and model of the controller.
        Returns ('Não informado', 'Não informado') if unknown.
        """
        if not descr_val:
            return "Não informado", "Não informado"

        descr = str(descr_val).strip()
        if not descr:
            return "Não informado", "Não informado"

        descr_upper = descr.upper()

        known_brands = [
            "SIEMENS",
            "PEEK",
            "SWARCO",
            "ECONOLITE",
            "DATAPROM",
            "TRAFFICWARE",
            "MCCAIN",
            "YUNEX",
            "COMPASS",
            "TELVENT",
            "KAPSCH",
        ]

        brand = "Não informado"
        for b in known_brands:
            if b in descr_upper:
                brand = b.title()
                break

        model_match = re.search(
            r"\b(ST\d{3,4}|M\d{2,3}|ATC[-_ ]?\d{4}|ASC[/-]?\d+|[A-Z]{1,4}[-_]?\d{3,4})\b", descr, re.IGNORECASE
        )
        if model_match:
            model = model_match.group(1).upper()
        else:
            model = descr if len(descr) <= 30 else descr[:30] + "..."

        return brand, model
