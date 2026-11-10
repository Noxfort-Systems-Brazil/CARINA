# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Contract for Emergency Vehicle Preemption (EVP) configuration repository (SOLID: ISP & DIP).
"""

from typing import Dict, List, Optional, Protocol, runtime_checkable

from src.evp.evp_models import RegisteredVehicle


@runtime_checkable
class IEVPConfigRepository(Protocol):
    """Protocol contract for EVP fleet configuration database persistence."""

    def save_vehicle(self, vehicle: RegisteredVehicle) -> bool:
        """Saves or updates an emergency vehicle registration record in the database."""
        ...

    def load_all_vehicles(self) -> Dict[str, RegisteredVehicle]:
        """Loads all authorized fleet vehicles persisted in the database."""
        ...

    def load_denied_vehicles(self) -> List[str]:
        """Loads the set of vehicle IDs explicitly marked as revoked/denied."""
        ...

    def remove_vehicle(self, vehicle_id: str) -> bool:
        """Removes a vehicle from the authorized table and registers it in the denied table."""
        ...

    def clear_all_vehicles(self) -> bool:
        """Removes all authorized vehicles from the database."""
        ...
