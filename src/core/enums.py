# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Defines shared enumerations (Enums) for the system core.

This file was created to resolve a circular dependency, isolating
the 'Maturity' Enum definition in a simple, dependency-free module.
"""

from enum import Enum, auto


class Maturity(Enum):
    """Defines an agent's maturity phases."""

    CHILD = auto()
    TEEN = auto()
    ADULT = auto()
