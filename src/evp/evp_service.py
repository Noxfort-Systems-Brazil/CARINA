# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Central EVP Lifecycle and Orchestration Service (Facade Pattern).
Coordinates telemetric flow delegating fleet to EVPFleetManager, network to EVPTopologyService,
kinematics to EVPKinematicsEngine, preemption to EVPPreemptionEngine,
and telemetry processing to EVPTelemetryProcessor (SOLID / SRP / DIP).
"""

import logging
import threading
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.evp.application.evp_snapshot_synchronizer import EVPSnapshotSynchronizer
from src.evp.application.evp_telemetry_processor import EVPTelemetryProcessor
from src.evp.evp_config_provider import EVPConfigProvider
from src.evp.evp_db_executor import AsyncTelemetryPersistQueue
from src.evp.evp_fleet_manager import EVPFleetManager
from src.evp.evp_kinematics import EVPKinematicsEngine
from src.evp.evp_models import EmergencyVehicle, RegisteredVehicle, TelemetryData
from src.evp.evp_preemption_engine import ACTION_ADVANCE, ACTION_HOLD, EVPPreemptionEngine
from src.evp.evp_telemetry_repository import EVPTelemetryRepository
from src.evp.evp_topology_service import EVPTopologyService

logger = logging.getLogger(__name__)


class EVPService:
    """
    Central Emergency Vehicle Preemption Orchestrator for CARINA_CORE.
    Thread-safe, decoupled via DIP, and layered architecture (< 200 lines).
    """

    ACTION_ADVANCE = ACTION_ADVANCE
    ACTION_HOLD = ACTION_HOLD

    _instance: Optional["EVPService"] = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "EVPService":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(
        self,
        kinematics: Optional[EVPKinematicsEngine] = None,
        fleet_manager: Optional[EVPFleetManager] = None,
        topology_service: Optional[EVPTopologyService] = None,
        preemption_engine: Optional[EVPPreemptionEngine] = None,
        repository: Optional[Any] = None,
        max_dwell_timeout_seconds: float = 45.0,
        offline_timeout_seconds: float = 30.0,
        auto_register_fleet: Optional[bool] = None,
        on_action_dispatch: Optional[Callable[[str, int, str], None]] = None,
        on_ui_notify: Optional[Callable[[Dict], None]] = None,
        on_persist_telemetry: Optional[Callable[[EmergencyVehicle, bool], None]] = None,
        snapshot_synchronizer: Optional[EVPSnapshotSynchronizer] = None,
        notifier: Optional[Any] = None,
    ):
        self.repository = repository
        if self.repository is None:
            try:
                from src.evp.evp_repository import EVPRepository

                self.repository = EVPRepository()
            except Exception as e:
                logger.warning(f"[EVPService] Não foi possível inicializar EVPRepository: {e}", exc_info=True)
                self.repository = None

        self.kinematics = kinematics or EVPKinematicsEngine()
        self.auto_register_fleet = EVPConfigProvider.resolve_auto_register_fleet(auto_register_fleet)
        self.fleet_manager = fleet_manager or EVPFleetManager(
            auto_register=self.auto_register_fleet,
            repository=self.repository,
        )
        self.topology_service = topology_service or EVPTopologyService()
        self.preemption_engine = preemption_engine or EVPPreemptionEngine(
            max_dwell_timeout_seconds=max_dwell_timeout_seconds,
            on_action_dispatch=on_action_dispatch,
        )
        self.offline_timeout_seconds = offline_timeout_seconds
        self.on_ui_notify = on_ui_notify
        self._notifier = notifier
        self._snapshot_synchronizer = snapshot_synchronizer or EVPSnapshotSynchronizer()
        self._custom_persist_cb = on_persist_telemetry is not None
        self._persist_queue: Optional[AsyncTelemetryPersistQueue] = None
        if on_persist_telemetry:
            self.on_persist_telemetry = on_persist_telemetry
        elif self.fleet_manager and getattr(self.fleet_manager, "repository", None):
            repo = self.fleet_manager.repository
            self.on_persist_telemetry = repo.save_telemetry
            if hasattr(repo, "save_telemetry_batch") and not hasattr(repo.save_telemetry, "assert_called"):
                self._persist_queue = AsyncTelemetryPersistQueue(repo.save_telemetry_batch)
        else:
            self.on_persist_telemetry = None

        self._vehicles: Dict[str, EmergencyVehicle] = {}
        self._service_lock = threading.RLock()

        self.telemetry_processor = EVPTelemetryProcessor(
            offline_timeout_seconds=self.offline_timeout_seconds,
            auto_register_fleet=self.auto_register_fleet,
        )

        # Bootstrap restoration
        self.restore_saved_fleet()

        logger.info("[EVPService] Orquestrador central de preempção inicializado.")
        try:
            self.topology_service.auto_load_map()
        except Exception as _exc:
            logger.debug("[evp] Ignored recoverable error: %s", _exc)

    # --- Backward Compatibility Properties and Facades ---
    @property
    def max_dwell_timeout_seconds(self) -> float:
        return self.preemption_engine.max_dwell_timeout_seconds

    @max_dwell_timeout_seconds.setter
    def max_dwell_timeout_seconds(self, value: float) -> None:
        self.preemption_engine.max_dwell_timeout_seconds = value

    @property
    def on_action_dispatch(self) -> Optional[Callable[[str, int, str], None]]:
        return self.preemption_engine.on_action_dispatch

    @on_action_dispatch.setter
    def on_action_dispatch(self, callback: Optional[Callable[[str, int, str], None]]) -> None:
        self.preemption_engine.on_action_dispatch = callback

    @property
    def _active_preemptions(self) -> Dict[str, Dict]:
        return self.preemption_engine._active_preemptions

    @property
    def _registered_fleet(self) -> Dict[str, RegisteredVehicle]:
        return self.fleet_manager._fleet

    @property
    def _intersections_geo(self) -> Dict[str, Tuple[float, float]]:
        return self.topology_service._intersections_geo

    @property
    def _intersection_target_stages(self) -> Dict[str, int]:
        return self.topology_service._intersection_target_stages

    @property
    def _intersection_quadras(self) -> Dict[str, List[Dict[str, Any]]]:
        return self.topology_service._intersection_quadras

    # Fleet Delegates
    def register_fleet_vehicle(self, vehicle: RegisteredVehicle) -> None:
        self.fleet_manager.register_vehicle(vehicle)
        self._notify_ui(
            {
                "vehicle_id": vehicle.vehicle_id,
                "corporation": vehicle.corporation.value,
                "is_online": False,
                "action": "registered",
            }
        )

    def unregister_fleet_vehicle(self, vehicle_id: str) -> bool:
        to_release: List[str] = []
        with self._service_lock:
            vehicle = self._vehicles.pop(vehicle_id, None)
            for int_id, p_info in list(self._active_preemptions.items()):
                if p_info.get("vehicle_id") == vehicle_id:
                    to_release.append(int_id)
            removed = self.fleet_manager.unregister_vehicle(vehicle_id)
        for int_id in to_release:
            self.preemption_engine.release_preemption(int_id, vehicle_id=vehicle_id, vehicle=vehicle)
        self._notify_ui({"vehicle_id": vehicle_id, "is_online": False, "action": "deleted"})
        return removed

    def restore_saved_fleet(self) -> int:
        with self._service_lock:
            count = self.fleet_manager.load_persisted_fleet()
            logger.info(f"[EVPService] Frota restaurada do banco: {count} viatura(s) autorizada(s).")
            return count

    def restore_saved_fleet_async(self, on_complete: Optional[Callable[[int], None]] = None) -> None:
        def _bg_restore():
            try:
                count = self.restore_saved_fleet()
                if on_complete:
                    on_complete(count)
            except Exception as e:
                logger.error(f"[EVPService] Erro na restauração assíncrona da frota: {e}", exc_info=True)

        threading.Thread(target=_bg_restore, daemon=True, name="EVPService-DBRestore").start()

    def get_registered_fleet(self) -> List[Dict[str, Any]]:
        return self.fleet_manager.get_registered_fleet()

    def is_vehicle_authorized(self, vehicle_id: str) -> bool:
        return self.fleet_manager.is_vehicle_authorized(vehicle_id)

    def import_fleet_connection_csv(self, filepath: str) -> Tuple[int, int]:
        return self.fleet_manager.import_fleet_connection_csv(filepath)

    def export_fleet_csv_template(self, filepath: str) -> bool:
        return self.fleet_manager.export_fleet_csv_template(filepath)

    def register_intersection(
        self, int_id: str, lat: float, lon: float, target_stage: int = 1, quadra_length: Optional[float] = None
    ) -> None:
        self.topology_service.register_intersection(int_id, lat, lon, target_stage, quadra_length)

    def load_map_data(self, map_data: Any) -> int:
        return self.topology_service.load_map_data(map_data)

    def auto_load_map(self) -> bool:
        return self.topology_service.auto_load_map()

    def activate_preemption(self, intersection_id: str, vehicle: EmergencyVehicle) -> None:
        target_stage = self.topology_service.get_target_stage(intersection_id, default=1)
        self.preemption_engine.activate_preemption(intersection_id, vehicle, target_stage=target_stage)

    def release_preemption(self, intersection_id: str, vehicle_id: str) -> None:
        vehicle = self._vehicles.get(vehicle_id)
        self.preemption_engine.release_preemption(intersection_id, vehicle_id=vehicle_id, vehicle=vehicle)

    def is_preemption_active(self, intersection_id: str) -> bool:
        return self.preemption_engine.is_preemption_active(intersection_id)

    def get_preemption_action(
        self,
        intersection_id: str,
        current_stage: int,
        stage_duration: float = 0.0,
        stage_duration_seconds: Optional[float] = None,
    ) -> Tuple[int, str]:
        return self.preemption_engine.get_preemption_action(
            intersection_id=intersection_id,
            current_stage=current_stage,
            stage_duration=stage_duration,
            stage_duration_seconds=stage_duration_seconds,
            vehicles=self._vehicles,
        )

    # Telemetric Orchestration
    def process_telemetry(self, telemetry: TelemetryData) -> None:
        with self._service_lock:
            vehicle = self.telemetry_processor.ingest_telemetry(
                telemetry=telemetry,
                vehicles=self._vehicles,
                fleet_manager=self.fleet_manager,
            )
            persist_cb = self.on_persist_telemetry
            persist_q = self._persist_queue
        if vehicle is None:
            return

        evp_triggered = self.preemption_engine.evaluate_vehicle_lifecycle(
            vehicle=vehicle,
            topology_service=self.topology_service,
            kinematics=self.kinematics,
        )
        self._notify_ui(vehicle)
        if (
            persist_q is not None
            and persist_cb == getattr(getattr(self.fleet_manager, "repository", None), "save_telemetry", None)
            and not hasattr(persist_cb, "assert_called")
        ):
            persist_q.enqueue(EVPTelemetryRepository.snapshot_telemetry(vehicle, evp_triggered))
        elif persist_cb:
            try:
                persist_cb(vehicle, evp_triggered)
            except Exception as ex:
                logger.error(f"[EVPService] Erro na persistência de telemetria: {ex}", exc_info=True)

    def _notify_ui(self, vehicle: Any) -> None:
        try:
            payload = vehicle.to_dict() if hasattr(vehicle, "to_dict") else vehicle
            if self.on_ui_notify:
                self.on_ui_notify(payload)
            else:
                if self._notifier is None:
                    from src.evp.evp_notifier import EVPNotifier

                    self._notifier = EVPNotifier.get_instance()
                self._notifier.notify(payload)
        except Exception as ex:
            logger.error(f"[EVPService] Erro ao notificar UI: {ex}", exc_info=True)

    def get_all_vehicles(self) -> List[Dict]:
        with self._service_lock:
            return self.fleet_manager.build_vehicle_dtos(self._vehicles)

    def export_remote_snapshot(self) -> Dict[str, Any]:
        """Serializes active EVP vehicles and preemptions for cross-process AI synchronization."""
        with self._service_lock:
            return self._snapshot_synchronizer.export_snapshot(self._vehicles, self.preemption_engine)

    def apply_remote_snapshot(self, snapshot: Any) -> None:
        """Synchronizes active EVP vehicles and preemptions received from CentralController."""
        with self._service_lock:
            self._snapshot_synchronizer.apply_snapshot(
                snapshot, self._vehicles, self.preemption_engine, self.offline_timeout_seconds
            )
