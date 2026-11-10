# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import Any, Callable

from src.evp.evp_models import EmergencyVehicle

logger = logging.getLogger(__name__)


class EVPTelemetryRepository:
    """Manages persistence and schema initialization for emergency vehicle telemetry audit records."""

    def __init__(self, engine: Any, close_conn_fn: Callable[[Any], None]):
        self.engine = engine
        self._close_conn = close_conn_fn
        self.ensure_table_exists()

    def ensure_table_exists(self) -> None:
        """Ensures the evp_telemetry_records table and index exist."""
        if not self.engine:
            return

        conn = None
        try:
            conn = self.engine.get_connection()
            if not conn:
                return

            cursor = conn.cursor()
            try:
                is_pg = getattr(self.engine, "db_type", "sqlite") == "postgres"
                if is_pg:
                    cursor.execute(
                        """
                        CREATE TABLE IF NOT EXISTS evp_telemetry_records (
                            id BIGSERIAL PRIMARY KEY,
                            vehicle_id VARCHAR(64) NOT NULL,
                            corporation VARCHAR(32) NOT NULL,
                            latitude DOUBLE PRECISION NOT NULL,
                            longitude DOUBLE PRECISION NOT NULL,
                            speed_kmh REAL NOT NULL,
                            heading_deg REAL NOT NULL,
                            siren_active BOOLEAN NOT NULL,
                            evp_triggered BOOLEAN NOT NULL DEFAULT FALSE,
                            intersection_id VARCHAR(64),
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                        """
                    )
                else:
                    cursor.execute(
                        """
                        CREATE TABLE IF NOT EXISTS evp_telemetry_records (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            vehicle_id TEXT NOT NULL,
                            corporation TEXT NOT NULL,
                            latitude REAL NOT NULL,
                            longitude REAL NOT NULL,
                            speed_kmh REAL NOT NULL,
                            heading_deg REAL NOT NULL,
                            siren_active BOOLEAN NOT NULL,
                            evp_triggered BOOLEAN NOT NULL DEFAULT 0,
                            intersection_id TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                        """
                    )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_evp_veh_time 
                    ON evp_telemetry_records(vehicle_id, created_at DESC);
                    """
                )
                if hasattr(conn, "commit"):
                    conn.commit()
            finally:
                try:
                    cursor.close()
                except Exception as _exc:
                    logger.debug("[evp] Ignored recoverable error: %s", _exc)
        except Exception as e:
            logger.warning(f"[EVPTelemetryRepository] Aviso ao verificar/criar tabela de telemetria: {e}", exc_info=True)
        finally:
            self._close_conn(conn)

    def save_telemetry(self, vehicle: EmergencyVehicle, evp_triggered: bool = False) -> bool:
        """Saves telemetry snapshot to the database for forensics and auditing."""
        if not self.engine:
            return False

        conn = None
        try:
            conn = self.engine.get_connection()
            if not conn:
                return False

            cursor = conn.cursor()
            try:
                is_pg = getattr(self.engine, "db_type", "sqlite") == "postgres"
                if is_pg:
                    cursor.execute(
                        """
                        INSERT INTO evp_telemetry_records (
                            vehicle_id, corporation, latitude, longitude,
                            speed_kmh, heading_deg, siren_active, evp_triggered, intersection_id
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                        """,
                        (
                            vehicle.vehicle_id,
                            vehicle.corporation.value,
                            vehicle.latitude,
                            vehicle.longitude,
                            vehicle.speed_kmh,
                            vehicle.heading_deg,
                            vehicle.siren_active,
                            evp_triggered,
                            vehicle.active_intersection_id,
                        ),
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO evp_telemetry_records (
                            vehicle_id, corporation, latitude, longitude,
                            speed_kmh, heading_deg, siren_active, evp_triggered, intersection_id
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            vehicle.vehicle_id,
                            vehicle.corporation.value,
                            vehicle.latitude,
                            vehicle.longitude,
                            vehicle.speed_kmh,
                            vehicle.heading_deg,
                            1 if vehicle.siren_active else 0,
                            1 if evp_triggered else 0,
                            vehicle.active_intersection_id,
                        ),
                    )
                if hasattr(conn, "commit"):
                    conn.commit()
                return True
            finally:
                try:
                    cursor.close()
                except Exception as _exc:
                    logger.debug("[evp] Ignored recoverable error: %s", _exc)
        except Exception as e:
            logger.error(f"[EVPTelemetryRepository] Erro ao salvar telemetria da viatura {vehicle.vehicle_id}: {e}", exc_info=True)
            return False
        finally:
            self._close_conn(conn)

