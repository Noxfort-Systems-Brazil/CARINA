# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Closed-loop hardware telemetry ingestion, remote proxy lifecycle synchronization,
stage decoding, ActionSupervisor timing updates, and F.E.N.I.X. transition alerts.
"""

import logging
from typing import Any, Callable, Dict, Optional

try:
    from src.drivers.hardware_telemetry_decoder import decode_stage_from_telemetry, resolve_tl_key
except ImportError:  # pragma: no cover
    from drivers.hardware_telemetry_decoder import decode_stage_from_telemetry, resolve_tl_key

logger = logging.getLogger(__name__)


def _default_evp_snapshot_sink(evp_state: Dict[str, Any]) -> None:
    try:
        from src.evp.evp_service import EVPService
    except ImportError:  # pragma: no cover
        from evp.evp_service import EVPService
    EVPService.get_instance().apply_remote_snapshot(evp_state)


class HardwareTelemetrySynchronizer:
    """Synchronizes upstream/local hardware telemetry and reconciles 0-based active stages."""

    def __init__(
        self,
        action_supervisor: Any,
        state_extractor: Optional[Any] = None,
        state_reconciler: Optional[Any] = None,
        telemetry_publisher: Optional[Any] = None,
        evp_snapshot_sink: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> None:
        self.action_supervisor = action_supervisor
        self.state_extractor = state_extractor
        self.state_reconciler = state_reconciler
        self.telemetry_publisher = telemetry_publisher
        self._evp_snapshot_sink = evp_snapshot_sink or _default_evp_snapshot_sink

    def sync(
        self,
        traffic_data: Dict[str, Any],
        agents: Dict[str, Any],
        sim_time: float,
        current_stages: Dict[str, Any],
    ) -> Dict[str, Dict[str, Any]]:
        """Syncs EVP state, hardware mirrors/proxies, missing telemetry polls, and decoded field stages."""
        self._sync_evp_snapshot(traffic_data)

        tls_telemetry = traffic_data.get("tls_telemetry")
        if not isinstance(tls_telemetry, dict):
            tls_telemetry = {}
            traffic_data["tls_telemetry"] = tls_telemetry

        hardware_status = self._extract_hardware_status(traffic_data)
        conn_mgr = getattr(self.action_supervisor, "connection_manager", None)
        if conn_mgr and hardware_status:
            self._sync_conn_mgr_mirror(conn_mgr, hardware_status)

        self._poll_and_update_drivers(conn_mgr, tls_telemetry, hardware_status)
        self._reconcile_decoded_stages(tls_telemetry, agents, sim_time, current_stages)
        return hardware_status

    def _sync_evp_snapshot(self, traffic_data: Dict[str, Any]) -> None:
        evp_state = traffic_data.get("evp_state")
        if not isinstance(evp_state, dict) or self._evp_snapshot_sink is None:
            return
        try:
            self._evp_snapshot_sink(evp_state)
        except Exception as exc:
            logger.debug(f"[HardwareTelemetrySynchronizer] EVP snapshot sync skipped: {exc}")

    @staticmethod
    def _extract_hardware_status(traffic_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        raw_hw_status = traffic_data.get("hardware_status")
        if not isinstance(raw_hw_status, dict):
            return {}
        return {str(k): dict(v) for k, v in raw_hw_status.items() if isinstance(v, dict)}

    def _sync_conn_mgr_mirror(self, conn_mgr: Any, hardware_status: Dict[str, Dict[str, Any]]) -> None:
        if hasattr(conn_mgr, "update_remote_hardware_status"):
            try:
                conn_mgr.update_remote_hardware_status(hardware_status)
            except Exception as exc:
                logger.debug(f"[HardwareTelemetrySynchronizer] Hardware status mirror update skipped: {exc}")
        self._sync_remote_driver_proxies(conn_mgr, hardware_status)

    def _sync_remote_driver_proxies(self, conn_mgr: Any, hardware_status: Dict[str, Dict[str, Any]]) -> None:
        try:
            from src.drivers.remote_proxy_synchronizer import sync_remote_driver_proxies
        except ImportError:  # pragma: no cover
            from drivers.remote_proxy_synchronizer import sync_remote_driver_proxies

        sync_remote_driver_proxies(
            conn_mgr=conn_mgr,
            hardware_status=hardware_status,
            pipe_conn=getattr(self.telemetry_publisher, "pipe_conn", None),
            state_extractor=self.state_extractor,
            prune_missing=False,
        )

    @staticmethod
    def _poll_and_update_drivers(
        conn_mgr: Any,
        tls_telemetry: Dict[str, Any],
        hardware_status: Dict[str, Dict[str, Any]],
    ) -> None:
        active_conns = getattr(conn_mgr, "active_connections", None)
        if not isinstance(active_conns, dict):
            return

        for tl_id, driver in list(active_conns.items()):
            if not getattr(driver, "is_connected", False):
                continue

            t_key = resolve_tl_key(tl_id, tls_telemetry)
            if t_key is not None and hasattr(driver, "update_telemetry"):
                try:
                    driver.update_telemetry(tls_telemetry[t_key])
                except Exception:
                    pass
            elif t_key is None and hasattr(driver, "get_status"):
                try:
                    status_data = driver.get_status()
                    if isinstance(status_data, dict):
                        tls_telemetry[tl_id] = status_data
                except Exception as exc:
                    logger.debug(f"[HardwareTelemetrySynchronizer] Direct telemetry poll failed for {tl_id}: {exc}")

            if resolve_tl_key(tl_id, hardware_status) is None and hasattr(conn_mgr, "get_hardware_info"):
                try:
                    info = conn_mgr.get_hardware_info(tl_id)
                    if isinstance(info, dict) and info.get("is_connected"):
                        hardware_status[tl_id] = {
                            "is_connected": True,
                            "brand": info.get("brand", "Desconectado"),
                            "model": info.get("model", "Desconectado"),
                            "protocol": info.get("protocol", "none"),
                        }
                except Exception:
                    pass

    def _reconcile_decoded_stages(
        self,
        tls_telemetry: Dict[str, Any],
        agents: Dict[str, Any],
        sim_time: float,
        current_stages: Dict[str, Any],
    ) -> None:
        green_map = getattr(self.state_extractor, "tl_green_stages", {})
        codes_map = getattr(self.state_extractor, "tl_stage_codes", {})
        if not isinstance(green_map, dict):
            green_map = {}
        if not isinstance(codes_map, dict):
            codes_map = {}

        for raw_tl_id, tel in list(tls_telemetry.items()):
            if not isinstance(tel, dict):
                continue

            target_id = resolve_tl_key(raw_tl_id, agents) or resolve_tl_key(raw_tl_id, current_stages) or raw_tl_id
            g_key = resolve_tl_key(target_id, green_map) or resolve_tl_key(raw_tl_id, green_map)
            c_key = resolve_tl_key(target_id, codes_map) or resolve_tl_key(raw_tl_id, codes_map)

            decoded = decode_stage_from_telemetry(
                tel,
                green_stages=green_map.get(g_key, []) if g_key else [],
                stage_codes=codes_map.get(c_key, {}) if c_key else {},
                current_stage_hint=current_stages.get(target_id),
            )
            if decoded is None or current_stages.get(target_id) == decoded:
                continue

            current_stages[target_id] = decoded
            if hasattr(self.action_supervisor, "record_stage_change"):
                self.action_supervisor.record_stage_change(target_id, sim_time)

            if self.state_reconciler is not None and hasattr(self.state_reconciler, "on_stage_transition_detected"):
                self.state_reconciler.on_stage_transition_detected(target_id, decoded)
                self.state_reconciler.on_stage_transition_detected(raw_tl_id, decoded)
