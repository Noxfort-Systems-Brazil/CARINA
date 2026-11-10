# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Backward compatibility adapter for AuditLogger.
Re-exports AuditLogger from src.security.audit_logger.
"""

from src.security.audit_logger import AuditLogger

__all__ = ["AuditLogger"]
