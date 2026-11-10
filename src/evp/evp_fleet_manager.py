# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Specialist Emergency Fleet Manager (EVP).
Strictly responsible for formal registration and in-memory authorization control (SRP).
Delegates CSV I/O to EVPFleetCsvService and DTO projection to EVPFleetDtoBuilder.
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Tuple

from src.evp.evp_fleet_csv_service import EVPFleetCsvService
from src.evp.evp_fleet_dto_builder import EVPFleetDtoBuilder
from src.evp.evp_models import RegisteredVehicle

logger = logging.getLogger(__name__)


class EVPFleetManager:
    """
    Thread-safe manager for authorized emergency vehicles and their network parameters.
    """

    def __init__(self, auto_register: bool = False, repository: Optional[Any] = None):
        self.auto_register = auto_register
        self.repository = repository
        if self.repository is None:
            try:
                from src.evp.evp_repository import EVPRepository

                self.repository = EVPRepository()
            except Exception as e:
                logger.warning(f"[EVPFleetManager] Não foi possível inicializar EVPRepository: {e}", exc_info=True)
                self.repository = None

        self._fleet: Dict[str, RegisteredVehicle] = {}
        self._unregistered_vehicles: set[str] = set()
        self._lock = threading.RLock()
        self.load_persisted_fleet()

    def load_persisted_fleet(self) -> int:
        """Loads registered vehicles persisted in database and unauthorized vehicles."""
        if self.repository:
            try:
                persisted = self.repository.get_registered_vehicles()
                with self._lock:
                    self._fleet = {v.vehicle_id: v for v in persisted}
                    self._unregistered_vehicles = set()
                    if hasattr(self.repository, "get_denied_vehicles"):
                        denied = self.repository.get_denied_vehicles()
                        self._unregistered_vehicles.update(denied)
                logger.info(f"[EVPFleetManager] {len(persisted)} viatura(s) carregada(s) do banco de dados.")
                return len(persisted)
            except Exception as e:
                logger.error(f"[EVPFleetManager] Erro ao carregar frota persistida: {e}", exc_info=True)
                return 0

        # Primary fallback: load via static repository EVPConfigRepository (Hardware Parity)
        try:
            from src.evp.evp_config_repo import EVPConfigRepository

            persisted = EVPConfigRepository.load_all_vehicles_db()
            denied = EVPConfigRepository.load_denied_vehicles_db()
            with self._lock:
                self._fleet = {v.vehicle_id: v for v in persisted}
                self._unregistered_vehicles = set(denied)
            logger.info(f"[EVPFleetManager] {len(persisted)} viatura(s) carregada(s) via EVPConfigRepository.")
            return len(persisted)
        except Exception as e:
            logger.error(f"[EVPFleetManager] Erro ao carregar frota via EVPConfigRepository: {e}", exc_info=True)
            return 0

    def register_vehicle(self, vehicle: RegisteredVehicle) -> None:
        """Formally registers a vehicle into the authorized municipal fleet."""
        with self._lock:
            self._unregistered_vehicles.discard(vehicle.vehicle_id)
            if self.repository and hasattr(self.repository, "remove_denied_vehicle"):
                try:
                    self.repository.remove_denied_vehicle(vehicle.vehicle_id)
                except Exception as e:
                    logger.debug(f"[EVPFleetManager] Erro ao remover viatura de negadas: {e}")

            self._fleet[vehicle.vehicle_id] = vehicle
            if self.repository:
                try:
                    self.repository.save_registered_vehicle(vehicle)
                except Exception as e:
                    logger.error(f"[EVPFleetManager] Erro ao persistir viatura {vehicle.vehicle_id}: {e}", exc_info=True)
            else:
                try:
                    from src.evp.evp_config_repo import EVPConfigRepository

                    EVPConfigRepository.save_vehicle_db(vehicle)
                except Exception as e:
                    logger.error(f"[EVPFleetManager] Erro ao persistir viatura {vehicle.vehicle_id} via EVPConfigRepository: {e}", exc_info=True)

            logger.info(
                f"[EVPFleetManager] Viatura {vehicle.vehicle_id} ({vehicle.corporation.value}) "
                f"cadastrada com sucesso. IP: {vehicle.ip_address}:{vehicle.port} [{vehicle.protocol}]."
            )

    def unregister_vehicle(self, vehicle_id: str) -> bool:
        """Formally unregisters a vehicle from the authorized municipal fleet."""
        with self._lock:
            removed = False
            if vehicle_id in self._fleet:
                del self._fleet[vehicle_id]
                removed = True

            self._unregistered_vehicles.add(vehicle_id)

            if self.repository:
                try:
                    db_removed = self.repository.delete_registered_vehicle(vehicle_id)
                    removed = removed or db_removed
                    if hasattr(self.repository, "add_denied_vehicle"):
                        self.repository.add_denied_vehicle(vehicle_id)
                except Exception as e:
                    logger.error(f"[EVPFleetManager] Erro ao remover viatura {vehicle_id} do banco: {e}", exc_info=True)
            else:
                try:
                    from src.evp.evp_config_repo import EVPConfigRepository

                    db_removed = EVPConfigRepository.remove_vehicle_db(vehicle_id)
                    removed = removed or db_removed
                except Exception as e:
                    logger.error(f"[EVPFleetManager] Erro ao remover viatura {vehicle_id} via EVPConfigRepository: {e}", exc_info=True)

            if removed:
                logger.info(f"[EVPFleetManager] Viatura {vehicle_id} removida da frota.")
            return removed

    def get_registered_fleet(self) -> List[Dict[str, Any]]:
        """Returns serialized list of all registered vehicles."""
        with self._lock:
            return [v.to_dict() for v in self._fleet.values() if v.vehicle_id not in self._unregistered_vehicles]

    def is_vehicle_unregistered(self, vehicle_id: str) -> bool:
        """Checks if vehicle was explicitly unauthorized/removed by operator."""
        with self._lock:
            return vehicle_id in self._unregistered_vehicles

    def is_vehicle_authorized(self, vehicle_id: str) -> bool:
        """Checks if vehicle has active authorization to request preemption."""
        with self._lock:
            if vehicle_id in self._unregistered_vehicles:
                return False
            if not self.auto_register:
                reg = self._fleet.get(vehicle_id)
                return bool(reg and reg.is_active)
            return True

    def get_vehicle(self, vehicle_id: str) -> Optional[RegisteredVehicle]:
        """Retrieves vehicle record if registered."""
        with self._lock:
            return self._fleet.get(vehicle_id)

    # --- CSV methods delegated to EVPFleetCsvService (Backward compatibility) ---
    @staticmethod
    def parse_csv_file(filepath: str) -> Tuple[List[RegisteredVehicle], int]:
        """Reads and parses fleet CSV file."""
        return EVPFleetCsvService.parse_csv_file(filepath)

    def import_fleet_connection_csv(self, filepath: str) -> Tuple[int, int]:
        """Imports CSV sheet with network and fleet parameters and persists into database."""
        imported_vehicles, total_rows = EVPFleetCsvService.parse_csv_file(filepath)
        success_count = 0

        with self._lock:
            for vehicle in imported_vehicles:
                self._unregistered_vehicles.discard(vehicle.vehicle_id)
                self._fleet[vehicle.vehicle_id] = vehicle
                success_count += 1

            if self.repository and imported_vehicles:
                try:
                    self.repository.save_registered_vehicles_batch(imported_vehicles)
                    if hasattr(self.repository, "remove_denied_vehicle"):
                        for iv in imported_vehicles:
                            self.repository.remove_denied_vehicle(iv.vehicle_id)
                except Exception as e:
                    logger.error(f"[EVPFleetManager] Erro ao persistir lote importado do CSV: {e}", exc_info=True)

        logger.info(f"[EVPFleetManager] Importação de frota concluída: {success_count}/{total_rows} viaturas.")
        return (success_count, total_rows)

    def export_fleet_csv_template(self, filepath: str) -> bool:
        """Exports CSV template with registered vehicles or standard example."""
        with self._lock:
            return EVPFleetCsvService.export_fleet_csv(filepath, self._fleet)

    # --- DTO method delegated to EVPFleetDtoBuilder (Backward compatibility) ---
    def build_vehicle_dtos(self, active_vehicles: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generates consolidated list of DTOs for UI display."""
        with self._lock:
            return EVPFleetDtoBuilder.build_vehicle_dtos(
                active_vehicles=active_vehicles,
                registered_fleet=self._fleet,
                unregistered_vehicles=self._unregistered_vehicles,
            )
