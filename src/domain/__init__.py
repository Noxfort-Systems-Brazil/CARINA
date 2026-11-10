# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
CARINA Core Domain Layer (DDD + Clean Architecture).
Pure Python domain models, rich entities, aggregate roots, value objects,
enumerations, and domain events. Strictly isolated from UI and infrastructure frameworks.
"""

from src.domain.entities import (
    AgentMaturity,
    EmergencyVehicle,
    IntersectionState,
    RegisteredVehicle,
    User,
)
from src.domain.enums import (
    CorporationType,
    FenixState,
    Maturity,
    SignalState,
    UserRole,
)
from src.domain.events import (
    AuthenticationFailedEvent,
    LockdownClearedEvent,
    LockdownTriggeredEvent,
    SecurityEvent,
    UserAuthenticatedEvent,
    UserRegisteredEvent,
    UserRemovedEvent,
)
from src.domain.value_objects import (
    AuthResult,
    FleetDecisions,
    IntersectionData,
    MaturityConfig,
    PasswordValidationResult,
    StageDefinition,
    TelemetryData,
)

__all__ = [
    "AgentMaturity",
    "EmergencyVehicle",
    "IntersectionState",
    "RegisteredVehicle",
    "User",
    "CorporationType",
    "FenixState",
    "Maturity",
    "SignalState",
    "UserRole",
    "AuthenticationFailedEvent",
    "LockdownClearedEvent",
    "LockdownTriggeredEvent",
    "SecurityEvent",
    "UserAuthenticatedEvent",
    "UserRegisteredEvent",
    "UserRemovedEvent",
    "AuthResult",
    "FleetDecisions",
    "IntersectionData",
    "MaturityConfig",
    "PasswordValidationResult",
    "StageDefinition",
    "TelemetryData",
]
