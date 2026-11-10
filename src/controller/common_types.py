# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Common Types
------------
Shared type definitions for the controller modules to avoid circular imports.
"""

from src.domain.enums import SignalState
from src.domain.value_objects import StageDefinition

__all__ = ["SignalState", "StageDefinition"]
