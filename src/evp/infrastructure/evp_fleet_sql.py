# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
EVP Fleet SQL Statements and Dialect Provider (Infrastructure Layer / SOLID: SRP).
Centralizes all DDL and DML queries for authorized and denied emergency fleets,
supporting PostgreSQL and SQLite dialects.
"""

from typing import Tuple


class EVPFleetSql:
    """Provides dialect-aware SQL statements for EVP fleet persistence."""

    CREATE_REGISTERED_FLEET_TABLE = """
        CREATE TABLE IF NOT EXISTS evp_registered_fleet (
            vehicle_id VARCHAR(64) PRIMARY KEY,
            corporation VARCHAR(32) NOT NULL,
            plate VARCHAR(16),
            description VARCHAR(128),
            device_id VARCHAR(64),
            ip_address VARCHAR(45),
            port INT DEFAULT 8085,
            protocol VARCHAR(16) DEFAULT 'HTTP',
            auth_token VARCHAR(128),
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """

    CREATE_DENIED_FLEET_TABLE = """
        CREATE TABLE IF NOT EXISTS evp_denied_fleet (
            vehicle_id VARCHAR(64) PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """

    SELECT_ALL_REGISTERED = """
        SELECT vehicle_id, corporation, plate, description,
               device_id, ip_address, port, protocol, auth_token, is_active
        FROM evp_registered_fleet;
    """

    SELECT_ALL_DENIED = """
        SELECT vehicle_id FROM evp_denied_fleet;
    """

    CLEAR_ALL_REGISTERED = "DELETE FROM evp_registered_fleet;"
    CLEAR_ALL_DENIED = "DELETE FROM evp_denied_fleet;"

    @classmethod
    def get_upsert_vehicle_query(cls, is_postgres: bool) -> str:
        if is_postgres:
            return """
                INSERT INTO evp_registered_fleet (
                    vehicle_id, corporation, plate, description,
                    device_id, ip_address, port, protocol, auth_token, is_active
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (vehicle_id) DO UPDATE SET
                    corporation = EXCLUDED.corporation,
                    plate = EXCLUDED.plate,
                    description = EXCLUDED.description,
                    device_id = EXCLUDED.device_id,
                    ip_address = EXCLUDED.ip_address,
                    port = EXCLUDED.port,
                    protocol = EXCLUDED.protocol,
                    auth_token = EXCLUDED.auth_token,
                    is_active = EXCLUDED.is_active;
            """
        return """
            INSERT INTO evp_registered_fleet (
                vehicle_id, corporation, plate, description,
                device_id, ip_address, port, protocol, auth_token, is_active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(vehicle_id) DO UPDATE SET
                corporation = excluded.corporation,
                plate = excluded.plate,
                description = excluded.description,
                device_id = excluded.device_id,
                ip_address = excluded.ip_address,
                port = excluded.port,
                protocol = excluded.protocol,
                auth_token = excluded.auth_token,
                is_active = excluded.is_active;
        """

    @classmethod
    def get_delete_registered_query(cls, is_postgres: bool) -> str:
        return "DELETE FROM evp_registered_fleet WHERE vehicle_id = %s;" if is_postgres else "DELETE FROM evp_registered_fleet WHERE vehicle_id = ?;"

    @classmethod
    def get_delete_denied_query(cls, is_postgres: bool) -> str:
        return "DELETE FROM evp_denied_fleet WHERE vehicle_id = %s;" if is_postgres else "DELETE FROM evp_denied_fleet WHERE vehicle_id = ?;"

    @classmethod
    def get_insert_denied_query(cls, is_postgres: bool) -> str:
        if is_postgres:
            return "INSERT INTO evp_denied_fleet (vehicle_id) VALUES (%s) ON CONFLICT (vehicle_id) DO NOTHING;"
        return "INSERT INTO evp_denied_fleet (vehicle_id) VALUES (?) ON CONFLICT(vehicle_id) DO NOTHING;"
