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
            logger.warning(
                f"[EVPTelemetryRepository] Aviso ao verificar/criar tabela de telemetria: {e}", exc_info=True
            )
        finally:
            self._close_conn(conn)

    @staticmethod
    def snapshot_telemetry(vehicle: EmergencyVehicle, evp_triggered: bool) -> tuple:
        """Captures an immutable telemetry row snapshot safe for cross-thread batching."""
        corp = getattr(vehicle.corporation, "value", vehicle.corporation)
        return (
            vehicle.vehicle_id,
            corp,
            vehicle.latitude,
            vehicle.longitude,
            vehicle.speed_kmh,
            vehicle.heading_deg,
            bool(vehicle.siren_active),
            bool(evp_triggered),
            vehicle.active_intersection_id,
        )

    @staticmethod
    def _format_row(item: Any, is_pg: bool) -> tuple:
        if isinstance(item, tuple) and len(item) == 9:
            v_id, corp, lat, lon, spd, hdg, siren, triggered, int_id = item
        else:
            veh, triggered = item
            corp = getattr(veh.corporation, "value", veh.corporation)
            v_id, lat, lon, spd, hdg, siren, int_id = (
                veh.vehicle_id,
                veh.latitude,
                veh.longitude,
                veh.speed_kmh,
                veh.heading_deg,
                bool(veh.siren_active),
                veh.active_intersection_id,
            )
        if is_pg:
            return (v_id, corp, lat, lon, spd, hdg, bool(siren), bool(triggered), int_id)
        return (v_id, corp, lat, lon, spd, hdg, 1 if siren else 0, 1 if triggered else 0, int_id)

    def save_telemetry_batch(self, items: list) -> int:
        """Persists a batch of telemetry snapshots or (vehicle, evp_triggered) tuples in one transaction."""
        if not self.engine or not items:
            return 0
        conn = None
        try:
            conn = self.engine.get_connection()
            if not conn:
                return 0
            cursor = conn.cursor()
            try:
                is_pg = getattr(self.engine, "db_type", "sqlite") == "postgres"
                ph = "%s, %s, %s, %s, %s, %s, %s, %s, %s" if is_pg else "?, ?, ?, ?, ?, ?, ?, ?, ?"
                sql = (
                    "INSERT INTO evp_telemetry_records "
                    "(vehicle_id, corporation, latitude, longitude, speed_kmh, heading_deg, "
                    f"siren_active, evp_triggered, intersection_id) VALUES ({ph});"
                )
                rows = [self._format_row(it, is_pg) for it in items]
                cursor.executemany(sql, rows)
                if hasattr(conn, "commit"):
                    conn.commit()
                return len(rows)
            finally:
                try:
                    cursor.close()
                except Exception as _exc:
                    logger.debug("[evp] Ignored recoverable error: %s", _exc)
        except Exception as e:
            if conn and hasattr(conn, "rollback"):
                try:
                    conn.rollback()
                except Exception:
                    pass
            logger.error(f"[EVPTelemetryRepository] Erro ao salvar lote de telemetria: {e}", exc_info=True)
            return 0
        finally:
            self._close_conn(conn)

    def save_telemetry(self, vehicle: EmergencyVehicle, evp_triggered: bool = False) -> bool:
        """Saves telemetry snapshot to the database for forensics and auditing."""
        return self.save_telemetry_batch([(vehicle, evp_triggered)]) > 0

    def purge_old_telemetry(self, keep_hours: int = 168) -> int:
        """Deletes EVP telemetry records older than `keep_hours` hours to bound storage growth."""
        if not self.engine or keep_hours <= 0:
            return 0
        conn = None
        try:
            conn = self.engine.get_connection()
            if not conn:
                return 0
            cursor = conn.cursor()
            try:
                is_pg = getattr(self.engine, "db_type", "sqlite") == "postgres"
                if is_pg:
                    cursor.execute(
                        "DELETE FROM evp_telemetry_records WHERE created_at < NOW() - make_interval(hours => %s::int);",
                        (int(keep_hours),),
                    )
                else:
                    cursor.execute(
                        "DELETE FROM evp_telemetry_records WHERE created_at < datetime('now', ? || ' hours');",
                        (f"-{int(keep_hours)}",),
                    )
                deleted = max(0, int(getattr(cursor, "rowcount", 0) or 0))
                if hasattr(conn, "commit"):
                    conn.commit()
                return deleted
            finally:
                try:
                    cursor.close()
                except Exception:
                    pass
        except Exception as e:
            if conn and hasattr(conn, "rollback"):
                try:
                    conn.rollback()
                except Exception:
                    pass
            logger.warning(f"[EVPTelemetryRepository] Error purging old telemetry records: {e}", exc_info=True)
            return 0
        finally:
            self._close_conn(conn)
