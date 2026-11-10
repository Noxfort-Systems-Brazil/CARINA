# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Domain Entities and Aggregate Roots (DDD).
Consolidates rich domain entities with encapsulated invariants and business behavior.
"""

from dataclasses import dataclass, field
from typing import List

from src.domain.enums import SignalState
from src.domain.value_objects import StageDefinition
from src.evp.evp_models import EmergencyVehicle, RegisteredVehicle
from src.maturity.agent_maturity import AgentMaturity
from src.security.models import User


@dataclass
class IntersectionState:
    """Runtime domain entity representing a single intersection's fixed-time cycle state."""

    tls_id: str
    phases: List[StageDefinition]
    current_phase_index: int = 0
    current_signal_state: SignalState = field(default=SignalState.ALL_RED)
    state_start_time: float = 0.0
    total_phase_changes: int = 0


__all__ = [
    "AgentMaturity",
    "EmergencyVehicle",
    "RegisteredVehicle",
    "IntersectionState",
    "User",
]
