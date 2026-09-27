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

# File: src/drivers/driver_factory.py
# Author: Gabriel Moraes
# Date: 2026-02-22

"""
Factory module for traffic light drivers.
Connects physical intersections via the compiled Go Hardware Gateway over OS standard pipes.
"""

import logging
import os
import re
from typing import Any, Optional

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

            res = client.connect_intersection(
                intersection_id=intersection_id,
                ip=ip_address,
                port=port,
                community=community_string,
                protocol="auto",
                green_stages=green_stages,
            )

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
            logger.error(f"[DriverFactory] Exception connecting to Go Gateway for [{ip_address}:{port}]: {e}")
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
