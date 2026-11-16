# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Synchronization helper materializing, updating, and pruning RemoteHardwareDriverProxy entries."""

import sys
from typing import Any, Dict, List, Optional

try:
    from src.drivers.hardware_telemetry_decoder import resolve_tl_key
    from src.drivers.remote_hardware_driver import RemoteHardwareDriverProxy
except ImportError:  # pragma: no cover
    from drivers.hardware_telemetry_decoder import resolve_tl_key
    from drivers.remote_hardware_driver import RemoteHardwareDriverProxy


def _is_remote_proxy(obj: Any) -> bool:
    """Checks RemoteHardwareDriverProxy membership across `src.drivers.*` and `drivers.*` aliases."""
    if obj is None:
        return False
    classes = [RemoteHardwareDriverProxy]
    for mod_name in ("src.drivers.remote_hardware_driver", "drivers.remote_hardware_driver"):
        mod = sys.modules.get(mod_name)
        cls = getattr(mod, "RemoteHardwareDriverProxy", None) if mod is not None else None
        if isinstance(cls, type) and cls not in classes:
            classes.append(cls)
    return isinstance(obj, tuple(classes))


def _extract_stage_meta(tl_id: str, state_extractor: Any) -> Dict[str, Any]:
    meta: Dict[str, Any] = {}
    if state_extractor is None:
        return meta
    g_map = getattr(state_extractor, "tl_green_stages", None)
    if isinstance(g_map, dict):
        g_key = resolve_tl_key(tl_id, g_map)
        if g_key is not None and isinstance(g_map[g_key], (list, tuple)):
            meta["green_stages"] = [int(x) for x in g_map[g_key]]
    c_map = getattr(state_extractor, "tl_stage_codes", None)
    if isinstance(c_map, dict):
        c_key = resolve_tl_key(tl_id, c_map)
        if c_key is not None and isinstance(c_map[c_key], dict):
            meta["stage_codes"] = {int(k): str(v) for k, v in c_map[c_key].items()}
    return meta


def _disconnect_proxy(active_conns: Dict[str, Any], key: str, disconnected_ids: List[str]) -> None:
    active_conns[key].shutdown()
    active_conns.pop(key, None)
    disconnected_ids.append(key)


def sync_remote_driver_proxies(
    conn_mgr: Any,
    hardware_status: Dict[str, Dict[str, Any]],
    pipe_conn: Optional[Any] = None,
    state_extractor: Any = None,
    prune_missing: bool = False,
) -> List[str]:
    """
    Materializes, updates, and optionally prunes RemoteHardwareDriverProxy entries in
    `conn_mgr.active_connections` when running under `CARINA_GATEWAY_ROLE=remote`.

    Returns a list of intersection IDs that transitioned to disconnected.
    """
    disconnected_ids: List[str] = []
    if conn_mgr is None or not isinstance(hardware_status, dict):
        return disconnected_ids

    try:
        from src.drivers.go_gateway_client import GoGatewayClient
    except ImportError:
        from drivers.go_gateway_client import GoGatewayClient

    if not GoGatewayClient.is_remote_gateway_role():
        return disconnected_ids

    active_conns = getattr(conn_mgr, "active_connections", None)
    if not isinstance(active_conns, dict):
        return disconnected_ids

    for raw_id, info in hardware_status.items():
        if not isinstance(info, dict):
            continue
        tl_id = str(raw_id)
        existing_key = resolve_tl_key(tl_id, active_conns)
        is_conn = bool(info.get("is_connected", False))
        stage_meta = _extract_stage_meta(tl_id, state_extractor)

        if is_conn:
            if existing_key is not None:
                drv = active_conns[existing_key]
                if _is_remote_proxy(drv):
                    merged_info = dict(info)
                    merged_info.update(stage_meta)
                    drv.update_from_status(merged_info)
                    if pipe_conn is not None:
                        drv.set_pipe_conn(pipe_conn)
            else:
                active_conns[tl_id] = RemoteHardwareDriverProxy(
                    intersection_id=tl_id,
                    ip_address=str(info.get("ip_address", "")),
                    protocol_name=str(info.get("protocol", "RemoteGatewayIPC")),
                    brand=str(info.get("brand", "Não informado")),
                    model=str(info.get("model", "Não informado")),
                    is_connected=True,
                    green_stages=stage_meta.get("green_stages"),
                    stage_codes=stage_meta.get("stage_codes"),
                    pipe_conn=pipe_conn,
                )
        elif existing_key is not None and _is_remote_proxy(active_conns[existing_key]):
            _disconnect_proxy(active_conns, existing_key, disconnected_ids)

    if prune_missing:
        for existing_id in list(active_conns.keys()):
            if not _is_remote_proxy(active_conns[existing_id]):
                continue
            h_key = resolve_tl_key(existing_id, hardware_status)
            if h_key is None or not hardware_status[h_key].get("is_connected", False):
                _disconnect_proxy(active_conns, existing_id, disconnected_ids)

    return disconnected_ids
