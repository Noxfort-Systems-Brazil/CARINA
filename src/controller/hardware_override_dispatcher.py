# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Dispatcher for manual hardware overrides, AI IPC commands, and Watchdog failsafe release."""

import logging
from typing import Any, Callable, Dict, List, Optional

try:
    from src.drivers.hardware_telemetry_decoder import resolve_tl_key
except ImportError:  # pragma: no cover
    from drivers.hardware_telemetry_decoder import resolve_tl_key

logger = logging.getLogger(__name__)


class HardwareOverrideDispatcher:
    """Dispatches manual operator overrides, AI IPC hardware commands, and failsafe releases."""

    _OVERRIDE_ACTION_BY_MODE: Dict[str, Dict[str, str]] = {
        "ALERT": {"action_type": "flash"},
        "OFF": {"action_type": "dark"},
    }
    _RELEASE_ACTION_BY_PREV_MODE: Dict[str, Dict[str, str]] = {
        "ALERT": {"action_type": "release_flash"},
        "OFF": {"action_type": "release_dark"},
    }

    def __init__(
        self,
        conn_mgr_provider: Callable[[bool], Optional[Any]],
        go_client_provider: Callable[[bool], Optional[Any]],
    ) -> None:
        self._conn_mgr_provider = conn_mgr_provider
        self._go_client_provider = go_client_provider
        self._active_overrides: Dict[str, str] = {}
        self._ai_cmd_handlers: Dict[str, Callable[[Any, Dict[str, Any]], bool]] = {
            "apply_action": self._ai_apply_action,
            "apply_logical_action": self._ai_apply_logical_action,
            "apply_decision": self._ai_apply_decision,
            "release_control": self._ai_release_control,
        }

    @staticmethod
    def resolve_active_driver(active_conns: Any, tl_id: str) -> Optional[Any]:
        """Resolves a driver entry from active_connections across tl_-prefixed/unprefixed variants."""
        if not isinstance(active_conns, dict):
            return None
        key = resolve_tl_key(str(tl_id), active_conns)
        return active_conns.get(key) if key is not None else None

    def _build_override_action(self, drv_key: str, tl_id: str, norm_mode: str) -> Dict[str, str]:
        override_action = self._OVERRIDE_ACTION_BY_MODE.get(norm_mode)
        if override_action is not None:
            self._active_overrides[drv_key] = norm_mode
            return dict(override_action)

        prev_mode = self._active_overrides.pop(drv_key, None) or self._active_overrides.pop(tl_id, None)
        release_action = self._RELEASE_ACTION_BY_PREV_MODE.get(str(prev_mode or ""), {"action_type": "release_hold"})
        return dict(release_action)

    def sync_override_to_hardware(self, target_tls: List[str], mode: str) -> None:
        """Applies immediate physical hardware override (flash / dark / release_flash / release_dark / release_hold)."""
        conn_mgr = self._conn_mgr_provider(False)
        if conn_mgr is None:
            return
        active_conns = getattr(conn_mgr, "active_connections", None)
        if not isinstance(active_conns, dict):
            return

        norm_mode = str(mode or "").upper()
        targets = (
            list(active_conns.keys())
            if not target_tls or "ALL" in [str(t).upper() for t in target_tls]
            else [str(t) for t in target_tls]
        )

        dispatched = set()
        for tl_id in targets:
            drv = self.resolve_active_driver(active_conns, tl_id)
            if drv is None or id(drv) in dispatched or not getattr(drv, "is_connected", False):
                continue
            dispatched.add(id(drv))
            drv_key = str(getattr(drv, "intersection_id", tl_id))
            action_data = self._build_override_action(drv_key, tl_id, norm_mode)
            try:
                if hasattr(drv, "log_carina_override"):
                    drv.log_carina_override(norm_mode)
                drv.apply_action(action_data)
            except Exception as exc:
                logger.debug(f"[HardwareOverrideDispatcher] Override sync failed for {tl_id}: {exc}")

    def execute_ai_hardware_cmd(self, payload: Dict[str, Any]) -> bool:
        """Executes hardware commands sent by AI_Process RemoteHardwareDriverProxy via command map."""
        if not isinstance(payload, dict):
            return False
        conn_mgr = self._conn_mgr_provider(True)
        if conn_mgr is None:
            return False

        tl_id = str(payload.get("intersection_id", ""))
        cmd = str(payload.get("cmd", "")).strip()
        handler = self._ai_cmd_handlers.get(cmd)
        if handler is None:
            return False

        driver = self.resolve_active_driver(getattr(conn_mgr, "active_connections", None), tl_id)
        if driver is None:
            return False

        try:
            return bool(handler(driver, payload))
        except Exception as exc:
            logger.debug(f"[HardwareOverrideDispatcher] execute_ai_hardware_cmd '{cmd}' error for {tl_id}: {exc}")
            return False

    @staticmethod
    def _ai_apply_action(driver: Any, payload: Dict[str, Any]) -> bool:
        return bool(driver.apply_action(payload.get("action_data") or {}))

    @staticmethod
    def _ai_apply_logical_action(driver: Any, payload: Dict[str, Any]) -> bool:
        raw_codes = payload.get("stage_codes")
        stage_codes = {int(k): str(v) for k, v in raw_codes.items()} if isinstance(raw_codes, dict) else None
        return bool(
            driver.apply_logical_action(
                int(payload.get("action", 1)),
                int(payload.get("current_stage_idx", 0)),
                [int(x) for x in (payload.get("green_stages") or [])],
                stage_codes=stage_codes,
            )
        )

    @staticmethod
    def _ai_apply_decision(driver: Any, payload: Dict[str, Any]) -> bool:
        return bool(driver.apply_decision(str(payload.get("action", "HOLD"))))

    @staticmethod
    def _ai_release_control(driver: Any, _payload: Dict[str, Any]) -> bool:
        hw = getattr(driver, "hardware_driver", None)
        if hw is not None and hasattr(hw, "release_control"):
            return bool(hw.release_control())
        return bool(driver.apply_action({"action_type": "release_hold"}))

    def on_failsafe_triggered(self) -> None:
        """Releases all connected drivers and sends emergency_release_all to GoGatewayClient."""
        conn_mgr = self._conn_mgr_provider(False)
        if conn_mgr is not None:
            active_conns = getattr(conn_mgr, "active_connections", None)
            if isinstance(active_conns, dict):
                for tl_id, driver in list(active_conns.items()):
                    if not getattr(driver, "is_connected", False):
                        continue
                    try:
                        if hasattr(driver, "apply_action"):
                            driver.apply_action({"action_type": "release_hold"})
                        elif hasattr(driver, "release_control"):
                            driver.release_control()
                    except Exception as exc:
                        logger.debug(f"[HardwareOverrideDispatcher] Failsafe release error for {tl_id}: {exc}")

        go_client = self._go_client_provider(False)
        if go_client is not None and getattr(go_client, "is_running", lambda: False)():
            try:
                go_client.emergency_release_all()
            except Exception as exc:
                logger.debug(f"[HardwareOverrideDispatcher] Go emergency_release_all error: {exc}")

    def on_failsafe_recovered(self) -> None:
        """Signals the Go gateway to resume heartbeats after Watchdog failsafe recovery."""
        go_client = self._go_client_provider(False)
        if go_client is not None and getattr(go_client, "is_running", lambda: False)():
            try:
                if hasattr(go_client, "resume_control_all"):
                    go_client.resume_control_all()
            except Exception as exc:
                logger.debug(f"[HardwareOverrideDispatcher] Go resume_control_all error: {exc}")
