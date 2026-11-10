# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Specialized service for serialization, template exporting, and CSV spreadsheet importing
for the emergency vehicle fleet (EVP).
Adheres to the Single Responsibility Principle (SRP) and Clean Architecture, isolating I/O
and parsing logic from relational database persistence.
"""

import csv
import io
import logging
from typing import Dict, List, Optional, Tuple

from src.evp.evp_models import CorporationType, RegisteredVehicle

logger = logging.getLogger(__name__)


class EVPFleetCsvService:
    """
    Exclusively responsible for parsing, validating, and exporting EVP fleet CSV data.
    """

    CSV_HEADERS: List[str] = [
        "vehicle_id",
        "corporation",
        "plate",
        "description",
        "device_id",
        "ip_address",
        "port",
        "protocol",
        "auth_token",
        "is_active",
    ]

    @classmethod
    def export_csv_template(cls, filepath: str, fleet: Optional[Dict[str, RegisteredVehicle]] = None) -> bool:
        """
        Generates a template or exports the current registered fleet to a CSV file in UTF-8 with BOM.
        """
        try:
            if not filepath.lower().endswith(".csv"):
                filepath = f"{filepath}.csv"
            with open(filepath, mode="w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(cls.CSV_HEADERS)
                if fleet:
                    for v in fleet.values():
                        writer.writerow([
                            v.vehicle_id,
                            v.corporation.value,
                            v.plate,
                            v.description,
                            v.device_id,
                            v.ip_address,
                            v.port,
                            v.protocol,
                            v.auth_token,
                            "true" if v.is_active else "false",
                        ])
                else:
                    writer.writerow(["SAMU-01", "SAMU", "ABC1D23", "Ambulância UTI 01", "IMEI-12345", "10.0.0.10", "8085", "HTTP", "", "true"])
                    writer.writerow(["BOMBEIRO-02", "BOMBEIRO", "XYZ9E87", "Auto Bomba Tanque", "IMEI-67890", "10.0.0.20", "8085", "HTTP", "", "true"])
                    writer.writerow(["POLICIA-03", "POLICIA", "POL2026", "Viatura Tática 03", "IMEI-11223", "10.0.0.30", "8085", "HTTP", "", "true"])

            logger.info(f"EVP fleet template exported successfully to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to export EVP fleet template: {e}", exc_info=True)
            return False

    @classmethod
    def export_fleet_csv(cls, filepath: str, fleet: Optional[Dict[str, RegisteredVehicle]] = None) -> bool:
        """Alias for export_csv_template for full compatibility with EVPFleetManager."""
        return cls.export_csv_template(filepath, fleet)

    @classmethod
    def parse_csv_file(cls, filepath: str) -> Tuple[List[RegisteredVehicle], int]:
        """
        Reads and parses fleet CSV file with support for UTF-8/BOM and multiple delimiters.
        Returns a tuple of (list_of_imported_vehicles, total_data_rows).
        """
        imported_vehicles: List[RegisteredVehicle] = []
        total_rows = 0
        try:
            with open(filepath, mode="r", encoding="utf-8-sig") as f:
                content = f.read()

            if not content.strip():
                logger.warning(f"CSV file is empty: {filepath}")
                return imported_vehicles, 0

            first_line = content.splitlines()[0] if content.splitlines() else ""
            delimiter = ","
            if ";" in first_line and first_line.count(";") >= first_line.count(","):
                delimiter = ";"
            elif "\t" in first_line and first_line.count("\t") > first_line.count(","):
                delimiter = "\t"

            reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)

            for row in reader:
                total_rows += 1
                v_id, plate, desc, dev_id, ip, token = "", "", "", "", "", ""
                corp = CorporationType.SAMU
                port = 8085
                protocol = "HTTP"
                active = True

                for key, val in row.items():
                    if not key:
                        continue
                    clean_k = key.strip().lstrip("\ufeff").strip().lower()
                    raw_v = str(val).strip() if val is not None else ""

                    if clean_k in ["vehicle_id", "id", "viatura", "id_viatura", "prefixo", "prefix"]:
                        v_id = raw_v.upper()
                    elif clean_k in ["corporation", "corporacao", "corporação", "tipo", "type"]:
                        corp = CorporationType.from_string(raw_v)
                    elif clean_k in ["plate", "placa"]:
                        plate = raw_v.upper()
                    elif clean_k in ["description", "descricao", "descrição", "modelo"]:
                        desc = raw_v
                    elif clean_k in ["device_id", "imei", "equipamento", "tracker"]:
                        dev_id = raw_v
                    elif clean_k in ["ip_address", "ip", "endereco_ip", "endereço_ip", "host"]:
                        ip = raw_v
                    elif clean_k in ["port", "porta"]:
                        try:
                            port = int(raw_v)
                        except ValueError:
                            port = 8085
                    elif clean_k in ["protocol", "protocolo"]:
                        protocol = raw_v.upper() or "HTTP"
                    elif clean_k in ["auth_token", "token", "senha", "secret"]:
                        token = raw_v
                    elif clean_k in ["is_active", "ativo", "active"]:
                        active = raw_v.lower() in ("true", "1", "yes", "sim", "t", "s")

                if v_id:
                    imported_vehicles.append(
                        RegisteredVehicle(
                            vehicle_id=v_id,
                            corporation=corp,
                            plate=plate,
                            description=desc or f"Viatura {v_id}",
                            device_id=dev_id,
                            ip_address=ip,
                            port=port,
                            protocol=protocol,
                            auth_token=token,
                            is_active=active,
                        )
                    )

            logger.info(f"Imported {len(imported_vehicles)}/{total_rows} EVP vehicles from CSV: {filepath}")
        except Exception as e:
            logger.error(f"Failed to parse EVP CSV file: {e}", exc_info=True)
        return imported_vehicles, total_rows

    @classmethod
    def import_csv_config(cls, filepath: str) -> List[RegisteredVehicle]:
        """
        Reads CSV file and returns the list of parsed registered vehicles.
        """
        imported_vehicles, _ = cls.parse_csv_file(filepath)
        return imported_vehicles
