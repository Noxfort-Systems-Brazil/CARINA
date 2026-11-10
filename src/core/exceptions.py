# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Domain exception hierarchy for CARINA road-traffic control and safety subsystems.
"""


class CarinaError(Exception):
    """Base exception for all CARINA domain errors."""


class SafetyViolationError(CarinaError):
    """Raised when a safety invariant (min green, intergreen clearance, or conflict matrix) is violated."""


class HardwareCommunicationError(CarinaError):
    """Raised when communication with a physical or simulated traffic controller fails."""


class FailsafeActivationError(CarinaError):
    """Raised when a fail-safe fallback transition encounters an error."""


class ConfigurationError(CarinaError):
    """Raised when configuration parsing or validation fails."""


class TelemetryDispatchError(CarinaError):
    """Raised when telemetry serialization or dispatch fails."""


class DatabaseError(CarinaError):
    """Raised when an underlying database query, transaction, or schema initialization fails."""


class SecurityError(CarinaError):
    """Raised when authentication, cryptographic, or security state operations fail."""


class EVPError(CarinaError):
    """Raised when emergency vehicle preemption routing or fleet coordination fails."""

