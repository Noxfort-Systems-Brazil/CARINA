# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
CSV spreadsheet repository adapter implementing IConnectionConfigCSVStorage (SRP).
Isolates CSV template generation, delimiter auto-detection, and SNMPv2c/v3 column parsing.
"""

import csv
import io
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

_ID_HEADERS = frozenset(
    {
        "intersection id",
        "intersection_id",
        "id do cruzamento",
        "id",
        "cruzamento",
        "agent_id",
        "intersection",
        "semaforo",
        "semáforo",
    }
)

_IP_HEADERS = frozenset(
    {
        "ip address",
        "ip_address",
        "endereço ip",
        "endereco ip",
        "ip",
        "ip_addr",
        "address",
        "host",
    }
)

_SNMP_CSV_KEY_MAP: Dict[str, str] = {
    "snmp_version": "snmp_version",
    "version": "snmp_version",
    "community": "community",
    "community_string": "community",
    "snmp_community": "community",
    "security_level": "security_level",
    "username": "username",
    "snmp_username": "username",
    "auth_protocol": "auth_protocol",
    "auth_passphrase": "auth_passphrase",
    "auth_password": "auth_passphrase",
    "priv_protocol": "priv_protocol",
    "priv_passphrase": "priv_passphrase",
    "priv_password": "priv_passphrase",
}


class ConnectionCSVStore:
    """Implements IConnectionConfigCSVStorage for intersection CSV import/export."""

    @staticmethod
    def _detect_delimiter(first_line: str) -> str:
        if ";" in first_line and first_line.count(";") >= first_line.count(","):
            return ";"
        if "\t" in first_line and first_line.count("\t") > first_line.count(","):
            return "\t"
        return ","

    def export_csv_template(self, filepath: str, saved_ips: Dict[str, str], known_intersections: List[str]) -> bool:
        """Generates a CSV template containing known intersections and their configured IPs."""
        try:
            target = filepath if filepath.lower().endswith(".csv") else f"{filepath}.csv"
            with open(target, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Intersection ID", "IP Address"])
                for tl_id in known_intersections:
                    writer.writerow([tl_id, saved_ips.get(tl_id, "")])
            logger.info(f"Hardware template exported successfully to {target}")
            return True
        except Exception as exc:
            logger.error(f"Failed to export hardware template: {exc}", exc_info=True)
            return False

    def import_csv_entries(self, filepath: str) -> Dict[str, Dict[str, Any]]:
        """Reads a CSV file into {intersection_id: {'ip': str, 'snmp_config': Optional[dict]}}."""
        entries: Dict[str, Dict[str, Any]] = {}
        try:
            with open(filepath, mode="r", encoding="utf-8-sig") as f:
                content = f.read()

            if not content.strip():
                logger.warning(f"CSV file is empty: {filepath}")
                return entries

            first_line = content.splitlines()[0] if content.splitlines() else ""
            delimiter = self._detect_delimiter(first_line)
            reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)

            for row in reader:
                tl_id = ""
                ip = ""
                snmp_cfg: Dict[str, Any] = {}
                for key, val in row.items():
                    if not key:
                        continue
                    clean_k = key.strip().lstrip("\ufeff").strip().lower()
                    clean_v = str(val).strip() if val else ""
                    if clean_k in _ID_HEADERS:
                        tl_id = clean_v
                    elif clean_k in _IP_HEADERS:
                        ip = clean_v
                    elif clean_k in _SNMP_CSV_KEY_MAP and clean_v:
                        snmp_cfg[_SNMP_CSV_KEY_MAP[clean_k]] = clean_v

                if tl_id and ip:
                    entries[tl_id] = {
                        "ip": ip,
                        "snmp_config": snmp_cfg if snmp_cfg else None,
                    }

            logger.info(f"Imported {len(entries)} configurations from CSV: {filepath}")
        except Exception as exc:
            logger.error(f"Failed to import CSV configuration: {exc}", exc_info=True)
        return entries

    def import_csv_config(self, filepath: str) -> Dict[str, str]:
        """Reads a CSV spreadsheet returning {intersection_id: ip_address}."""
        entries = self.import_csv_entries(filepath)
        return {tl_id: entry["ip"] for tl_id, entry in entries.items()}
