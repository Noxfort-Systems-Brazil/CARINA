# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Immutable Domain Events (DDD).
Consolidates domain events emitted across CARINA bounded contexts.
"""

from src.security.events import (
    AuthenticationFailedEvent,
    LockdownClearedEvent,
    LockdownTriggeredEvent,
    SecurityEvent,
    UserAuthenticatedEvent,
    UserRegisteredEvent,
    UserRemovedEvent,
)

__all__ = [
    "SecurityEvent",
    "UserAuthenticatedEvent",
    "AuthenticationFailedEvent",
    "LockdownTriggeredEvent",
    "LockdownClearedEvent",
    "UserRegisteredEvent",
    "UserRemovedEvent",
]
