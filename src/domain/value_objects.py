# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Domain Value Objects (DDD).
Canonical, dependency-free value structures shared across CARINA bounded contexts.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from src.evp.evp_models import TelemetryData
from src.maturity.maturity_config import MaturityConfig
from src.security.models import AuthResult, PasswordValidationResult


@dataclass
class StageDefinition:
    """
    A single signal stage/phase extracted from the SUMO TLS program.

    Attributes:
        state_string: Raw SUMO state (e.g., "GGrrrrGGrrrr") defining which
                      signal links are green/red in this stage.
        yellow_string: Derived state where all G/g are replaced with 'y'.
        all_red_string: All characters set to 'r' for clearance interval.
    """

    state_string: str
    yellow_string: str
    all_red_string: str


@dataclass
class IntersectionData:
    """Value Object encapsulating static phase definitions for an intersection."""

    tls_id: str
    phase_definitions: List[StageDefinition]


@dataclass
class FleetDecisions:
    """Consolidated decisions and metrics across all evaluated agents in a step."""

    actions: Dict[str, int] = field(default_factory=dict)
    lanes_state: Dict[str, Dict[str, str]] = field(default_factory=dict)
    maturity_info: Dict[str, str] = field(default_factory=dict)
    step_reward_sum: float = 0.0
    guardian_vetoed_any: bool = False
    metrics_delta: Dict[str, Tuple[float, float]] = field(default_factory=dict)


__all__ = [
    "StageDefinition",
    "IntersectionData",
    "FleetDecisions",
    "TelemetryData",
    "MaturityConfig",
    "AuthResult",
    "PasswordValidationResult",
]
