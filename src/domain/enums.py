# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Domain Enumerations (DDD: Ubiquitous Language).
Pure Python enumerations with zero external framework or infrastructure dependencies.
"""

from enum import Enum

from src.core.enums import Maturity
from src.evp.evp_models import CorporationType
from src.fenix.protocols import FenixState
from src.security.models import UserRole


class SignalState(Enum):
    """NEMA-compliant signal states for a phase transition."""

    GREEN = "GREEN"
    YELLOW = "YELLOW"
    ALL_RED = "ALL_RED"


__all__ = [
    "Maturity",
    "SignalState",
    "CorporationType",
    "FenixState",
    "UserRole",
]
