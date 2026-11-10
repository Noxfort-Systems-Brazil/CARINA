# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Emergency Vehicle Preemption (EVP) Module for CARINA_CORE.
Ensures safe passage (Green Corridor) for SAMU, Fire Department, and Police in compliance with CONTRAN.
"""

from src.evp.evp_fleet_manager import EVPFleetManager
from src.evp.evp_models import CorporationType, EmergencyVehicle, RegisteredVehicle
from src.evp.evp_preemption_engine import ACTION_ADVANCE, ACTION_HOLD, EVPPreemptionEngine
from src.evp.evp_service import EVPService
from src.evp.evp_topology_service import EVPTopologyService

__all__ = [
    "CorporationType",
    "EmergencyVehicle",
    "RegisteredVehicle",
    "EVPService",
    "EVPFleetManager",
    "EVPTopologyService",
    "EVPPreemptionEngine",
    "ACTION_ADVANCE",
    "ACTION_HOLD",
]
