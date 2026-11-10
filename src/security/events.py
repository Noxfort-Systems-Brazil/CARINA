# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Domain Events for the Security Subsystem (DDD).
Defines immutable domain events emitted during authentication, lockdown, and user lifecycles.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class SecurityEvent:
    """Base domain event for security actions."""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass(frozen=True)
class UserAuthenticatedEvent(SecurityEvent):
    """Emitted when a user successfully authenticates."""
    username: str = ""
    role: str = ""


@dataclass(frozen=True)
class AuthenticationFailedEvent(SecurityEvent):
    """Emitted when an authentication attempt fails."""
    username: str = ""
    reason: str = ""


@dataclass(frozen=True)
class LockdownTriggeredEvent(SecurityEvent):
    """Emitted when system rate-limiting activates persistent lockdown."""
    failed_attempts: int = 0
    reason: str = ""


@dataclass(frozen=True)
class LockdownClearedEvent(SecurityEvent):
    """Emitted when lockdown is cleared by an authorized superuser or master."""
    cleared_by: str = ""


@dataclass(frozen=True)
class UserRegisteredEvent(SecurityEvent):
    """Emitted when a new user account is created or updated."""
    username: str = ""
    role: str = ""


@dataclass(frozen=True)
class UserRemovedEvent(SecurityEvent):
    """Emitted when a user account is deleted."""
    username: str = ""
