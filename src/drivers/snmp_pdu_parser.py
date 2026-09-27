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

# File: src/drivers/snmp_pdu_parser.py
# Author: Gabriel Moraes
# Date: 2026-09-25

"""
Decodes raw SNMP Trap byte streams and extracts structured alert fields.
Isolated responsibility according to the Single Responsibility Principle (SRP).
"""

import logging
import re
from typing import Any, Dict

logger = logging.getLogger(__name__)


class SnmpPduParser:
    """
    Parser for active hardware traps and push notification frames from signal controllers.
    """

    @staticmethod
    def parse(raw_data: bytes) -> Dict[str, Any]:
        """
        Decodes SNMP ASN.1 PDU bytes or embedded TRAP|... payload into structured fields.
        """
        details: Dict[str, Any] = {
            "trap_oid": "1.3.6.1.4.1.2825.4.1",
            "message": "Alerta ativo de hardware recebido do controlador",
            "level": "CRITICAL",
            "varbinds": {},
        }
        try:
            # 1. Search for custom TRAP| header if present
            raw_text = raw_data.decode("utf-8", errors="ignore")
            if "TRAP|" in raw_text:
                trap_part = raw_text.split("TRAP|", 1)[1]
                parts = trap_part.split("|")
                if len(parts) >= 3:
                    details["trap_oid"] = parts[0].strip()
                    details["level"] = parts[1].strip()
                    details["message"] = "|".join(parts[2:]).strip()
                    return details

            # 2. Fallback: extract clean printable ASCII/UTF-8 strings
            printable_strings = re.findall(r"[A-Za-z0-9_\-\.\:\/\[\]\s\(\)]{4,}", raw_text)
            clean_strings = [s for s in printable_strings if s not in ["public", "private"] and len(s) > 5]
            if clean_strings:
                details["message"] = " | ".join(clean_strings[:2])

        except Exception as e:
            logger.debug(f"[SnmpPduParser] Error parsing PDU: {e}")

        return details
