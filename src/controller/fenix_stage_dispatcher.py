# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Coordinates F.E.N.I.X. post-resurrection field stage reconciliation and handover completion.
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    from src.controller.hardware_command_service import HardwareCommandService
    from src.drivers.hardware_telemetry_decoder import decode_stage_from_telemetry, resolve_tl_key
except ImportError:  # pragma: no cover
    from controller.hardware_command_service import HardwareCommandService
    from drivers.hardware_telemetry_decoder import decode_stage_from_telemetry, resolve_tl_key

logger = logging.getLogger(__name__)


def _default_green_stages_lookup(tl_id: str) -> List[int]:
    try:
        from src.controller.map_discoverer import MapTopologyDiscoverer
    except ImportError:  # pragma: no cover
        from controller.map_discoverer import MapTopologyDiscoverer
    return MapTopologyDiscoverer.get_green_stages(tl_id) or []


def _default_stage_codes_lookup(tl_id: str, locale_manager: Optional[Any]) -> Dict[int, str]:
    try:
        from src.drivers.traffic_map_loader import TrafficMapLoader
    except ImportError:  # pragma: no cover
        from drivers.traffic_map_loader import TrafficMapLoader
    return TrafficMapLoader.load_stage_states(tl_id, locale_manager=locale_manager) or {}


class FenixStageDispatcher:
    """Builds authoritative field-stage snapshots and manages F.E.N.I.X. handover signaling."""

    def __init__(
        self,
        conn_mgr_provider: Callable[[bool], Optional[Any]],
        refresh_snapshots: Callable[[bool], Tuple[Dict[str, Any], Dict[str, Any], Optional[Dict[str, Any]]]],
        topology_manager: Optional[Any] = None,
        ai_pipe_provider: Optional[Callable[[], Optional[Any]]] = None,
        fenix_queue_provider: Optional[Callable[[], Optional[Any]]] = None,
        locale_manager: Optional[Any] = None,
        green_stages_lookup: Optional[Callable[[str], List[int]]] = None,
        stage_codes_lookup: Optional[Callable[[str, Optional[Any]], Dict[int, str]]] = None,
    ) -> None:
        self._conn_mgr_provider = conn_mgr_provider
        self._refresh_snapshots = refresh_snapshots
        self.topology_manager = topology_manager
        self._ai_pipe_provider = ai_pipe_provider
        self._fenix_queue_provider = fenix_queue_provider
        self.locale_manager = locale_manager
        self._green_stages_lookup = green_stages_lookup or _default_green_stages_lookup
        self._stage_codes_lookup = stage_codes_lookup or _default_stage_codes_lookup

    def get_stage_metadata(self, tl_id: str, conn_mgr: Optional[Any]) -> Tuple[List[int], Dict[int, str]]:
        """Resolves green_stages and stage_codes from active driver first, falling back to map discovery."""
        green_stages: List[int] = []
        stage_codes: Dict[int, str] = {}

        driver = (
            HardwareCommandService.resolve_active_driver(getattr(conn_mgr, "active_connections", None), tl_id)
            if conn_mgr is not None
            else None
        )
        if driver is not None:
            raw_g = getattr(driver, "green_stages", None)
            if isinstance(raw_g, (list, tuple)):
                green_stages = [int(x) for x in raw_g]
            raw_codes = getattr(driver, "stage_states", None)
            if isinstance(raw_codes, dict):
                stage_codes = {int(k): str(v) for k, v in raw_codes.items()}

        if not green_stages:
            try:
                green_stages = self._green_stages_lookup(tl_id) or []
            except Exception:
                green_stages = []

        if not stage_codes:
            try:
                stage_codes = self._stage_codes_lookup(tl_id, self.locale_manager) or {}
            except Exception:
                stage_codes = {}

        return green_stages, stage_codes

    def _resolve_intersection_stage(
        self,
        tl_id: str,
        tls_telemetry: Dict[str, Any],
        conn_mgr: Optional[Any],
        cache_dict: Dict[str, Any],
    ) -> int:
        c_key = resolve_tl_key(tl_id, cache_dict)
        hint_raw = cache_dict.get(c_key) if c_key is not None else None
        hint = hint_raw.get("phase") if isinstance(hint_raw, dict) else hint_raw

        t_key = resolve_tl_key(tl_id, tls_telemetry)
        if t_key is not None:
            green_stages, stage_codes = self.get_stage_metadata(tl_id, conn_mgr)
            decoded = decode_stage_from_telemetry(
                tls_telemetry[t_key],
                green_stages=green_stages,
                stage_codes=stage_codes,
                current_stage_hint=hint if isinstance(hint, int) else None,
            )
            if decoded is not None:
                return int(decoded)

        cached = hint_raw if c_key is not None else 0
        if isinstance(cached, dict):
            cached = cached.get("phase", cached.get("stage", 0))
        try:
            return int(cached or 0)
        except (TypeError, ValueError):
            return 0

    def dispatch_fenix_reconcile_stages(self, ai_pipe_conn: Optional[Any] = None) -> Dict[str, int]:
        """Builds field stage map and dispatches ('fenix', 'reconcile_stages', (stages,), {}) to AI_Process."""
        tls_telemetry, _, _ = self._refresh_snapshots(False)
        conn_mgr = self._conn_mgr_provider(False)

        phases_cache = getattr(self.topology_manager, "tls_phases_cache", None)
        cache_dict = phases_cache if isinstance(phases_cache, dict) else {}

        all_ids = set(str(k) for k in cache_dict.keys()) | set(str(k) for k in tls_telemetry.keys())
        if conn_mgr is not None and isinstance(getattr(conn_mgr, "active_connections", None), dict):
            all_ids.update(str(k) for k in conn_mgr.active_connections.keys())

        stages = {
            tl_id: self._resolve_intersection_stage(tl_id, tls_telemetry, conn_mgr, cache_dict)
            for tl_id in sorted(all_ids)
        }

        pipe = ai_pipe_conn or (self._ai_pipe_provider() if self._ai_pipe_provider is not None else None)
        if pipe is not None and not getattr(pipe, "closed", False):
            try:
                pipe.send(("fenix", "reconcile_stages", (stages,), {}))
                logger.info(
                    f"[FenixStageDispatcher] Dispatched F.E.N.I.X. reconcile_stages for {len(stages)} intersections."
                )
            except Exception as exc:
                logger.warning(f"[FenixStageDispatcher] Failed to dispatch reconcile_stages: {exc}")

        return stages

    def handle_fenix_handover_complete(self, payload: Optional[Dict[str, Any]] = None) -> bool:
        """Signals ProcessManager's fenix_queue that AI_Process completed handover reconciliation."""
        fenix_queue = self._fenix_queue_provider() if self._fenix_queue_provider is not None else None
        if fenix_queue is None:
            return False
        try:
            fenix_queue.put_nowait(("HANDOVER_COMPLETE", dict(payload or {})))
            return True
        except Exception as exc:
            logger.warning(f"[FenixStageDispatcher] Failed to signal HANDOVER_COMPLETE: {exc}")
            return False
