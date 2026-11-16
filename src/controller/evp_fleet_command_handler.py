# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Handler for UI EVP fleet mutations and AI_Process EVP preemption Go-gateway dispatch."""

import logging
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class EvpFleetCommandHandler:
    """Executes EVP fleet registration, CSV import, restore, and preemption commands."""

    def __init__(
        self,
        evp_service_provider: Callable[[bool], Optional[Any]],
        go_client_provider: Callable[[bool], Optional[Any]],
        refresh_snapshots: Callable[[bool], Any],
    ) -> None:
        self._evp_service_provider = evp_service_provider
        self._go_client_provider = go_client_provider
        self._refresh_snapshots = refresh_snapshots
        self._fleet_handlers: Dict[str, Callable[[Any, Dict[str, Any]], bool]] = {
            "register": self._evp_register,
            "unregister": self._evp_unregister,
            "import_csv": self._evp_import_csv,
            "sync": self._evp_sync,
        }

    @staticmethod
    def _build_registered_vehicle(data: Dict[str, Any]) -> Any:
        try:
            from src.evp.evp_models import CorporationType, RegisteredVehicle
        except ImportError:  # pragma: no cover
            from evp.evp_models import CorporationType, RegisteredVehicle

        return RegisteredVehicle(
            vehicle_id=str(data.get("vehicle_id", "")).strip(),
            corporation=CorporationType.from_string(data.get("corporation", "SAMU")),
            plate=str(data.get("plate", "")),
            description=str(data.get("description", "")),
        )

    def _evp_register(self, evp_svc: Any, payload: Dict[str, Any]) -> bool:
        veh_data = payload.get("vehicle") or payload
        if not str(veh_data.get("vehicle_id", "")).strip():
            return False
        evp_svc.register_fleet_vehicle(self._build_registered_vehicle(veh_data))
        return True

    @staticmethod
    def _evp_unregister(evp_svc: Any, payload: Dict[str, Any]) -> bool:
        veh_id = str(payload.get("vehicle_id", "")).strip()
        return bool(evp_svc.unregister_fleet_vehicle(veh_id)) if veh_id else False

    def _evp_import_csv(self, evp_svc: Any, payload: Dict[str, Any]) -> bool:
        filepath = payload.get("filepath")
        if filepath:
            ok_cnt, _ = evp_svc.import_fleet_connection_csv(str(filepath))
            return ok_cnt > 0
        vehicles = payload.get("vehicles")
        if isinstance(vehicles, list):
            for item in vehicles:
                if isinstance(item, dict) and item.get("vehicle_id"):
                    evp_svc.register_fleet_vehicle(self._build_registered_vehicle(item))
            return True
        return False

    @staticmethod
    def _evp_sync(evp_svc: Any, _payload: Dict[str, Any]) -> bool:
        evp_svc.restore_saved_fleet()
        return True

    def set_evp_fleet(self, payload: Dict[str, Any]) -> bool:
        """Applies EVP fleet mutations from UI on owner EVPService via action dispatch table."""
        evp_svc = self._evp_service_provider(True)
        if evp_svc is None or not isinstance(payload, dict):
            return False

        action = str(payload.get("action", "")).lower()
        handler = self._fleet_handlers.get(action)
        ok = False
        if handler is not None:
            try:
                ok = bool(handler(evp_svc, payload))
            except Exception as exc:
                logger.error(f"[EvpFleetCommandHandler] set_evp_fleet error: {exc}", exc_info=True)
                ok = False

        self._refresh_snapshots(False)
        return ok

    def execute_ai_evp_preempt(self, payload: Dict[str, Any]) -> bool:
        """Executes EVP preemption commands forwarded by AI_Process on GoGatewayClient."""
        if not isinstance(payload, dict):
            return False
        go_client = self._go_client_provider(True)
        if go_client is None or not go_client.is_running():
            return False
        res = go_client.send_command(
            "evp_preempt",
            intersection_id=payload.get("intersection_id"),
            action_data=payload.get("action_data") or {},
        )
        return bool(isinstance(res, dict) and res.get("success", False))
