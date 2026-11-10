# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Security Audit Logger (SOLID: SRP).
Persists structured security events (logins, account changes, policy rejections, lockdowns).
Provides dual persistence: resilient local JSON ledger + central database logging.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.utils.paths import get_base_output_dir, get_user_config_dir

logger = logging.getLogger("AuditLogger")


class AuditLogger:
    """
    Registers audit actions (who, when, what) with dual persistence:
    - Resilient local JSON ledger (edge-guaranteed)
    - Central relational database table (PostgreSQL/SQLite) when available.
    """

    def __init__(
        self,
        config_dir: Optional[str] = None,
        db_engine: Optional[Any] = None,
        locale_manager: Optional[object] = None,
    ):
        self.locale_manager = locale_manager
        self.db_engine = db_engine

        target_dir = config_dir or os.path.join(get_base_output_dir(), "results")
        self.audit_file = os.path.join(target_dir, "audit_log.json")
        self._ensure_file()

    def _ensure_file(self) -> None:
        try:
            os.makedirs(os.path.dirname(self.audit_file), exist_ok=True)
            if not os.path.exists(self.audit_file):
                self._save_data([])
        except Exception as e:
            logger.error(f"Error ensuring audit file: {e}", exc_info=True)

    def _load_data(self) -> List[Dict[str, Any]]:
        try:
            with open(self.audit_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading audit log: {e}", exc_info=True)
            return []

    def _save_data(self, data: List[Dict[str, Any]]) -> None:
        try:
            with open(self.audit_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving audit log: {e}", exc_info=True)

    def log_action(self, username: str, action: str, details: str = "") -> None:
        """Records an action in the audit log (both local JSON and central Database)."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "username": username or "SYSTEM",
            "action": action,
            "details": details,
        }

        # 1. Local JSON persistence
        data = self._load_data()
        data.append(entry)
        if len(data) > 1000:
            data = data[-1000:]
        self._save_data(data)

        # 2. Central Database persistence
        if self.db_engine:
            try:
                conn = self.db_engine.get_connection() if hasattr(self.db_engine, "get_connection") else self.db_engine
                if conn:
                    cursor = conn.cursor()
                    placeholder = "%s" if getattr(self.db_engine, "db_type", "sqlite") == "postgres" else "?"
                    cursor.execute(
                        f"INSERT INTO security_audit_logs (created_at, username, action, details) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})",
                        (entry["timestamp"], entry["username"], entry["action"], entry["details"]),
                    )
                    if hasattr(conn, "commit"):
                        conn.commit()
            except Exception as dbe:
                logger.debug(f"[DB AUDIT] Database record skipped (offline or uninitialized): {dbe}")

        logger.info(f"[AUDIT] User '{username}' executed '{action}'. Details: {details}")

    def get_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Returns the most recent logs first, preferring DB and falling back to JSON."""
        if self.db_engine:
            try:
                conn = self.db_engine.get_connection() if hasattr(self.db_engine, "get_connection") else self.db_engine
                if conn:
                    cursor = conn.cursor()
                    placeholder = "%s" if getattr(self.db_engine, "db_type", "sqlite") == "postgres" else "?"
                    cursor.execute(
                        f"SELECT created_at, username, action, details FROM security_audit_logs ORDER BY created_at DESC LIMIT {placeholder}",
                        (limit,),
                    )
                    rows = cursor.fetchall()
                    if rows:
                        return [
                            {
                                "timestamp": r[0].isoformat() if hasattr(r[0], "isoformat") else str(r[0]),
                                "username": r[1],
                                "action": r[2],
                                "details": r[3] or "",
                            }
                            for r in rows
                        ]
            except Exception as dbe:
                logger.debug(f"[DB AUDIT] Database fetch fallback to JSON: {dbe}")

        data = self._load_data()
        return list(reversed(data))[:limit]

    def log_event(self, event: Any) -> None:
        """Processes and records a domain SecurityEvent."""
        from src.security.events import (
            AuthenticationFailedEvent,
            LockdownClearedEvent,
            LockdownTriggeredEvent,
            UserAuthenticatedEvent,
            UserRegisteredEvent,
            UserRemovedEvent,
        )

        if isinstance(event, UserAuthenticatedEvent):
            self.log_action(event.username, "AUTH_LOGIN_SUCCESS", f"Role: {event.role}")
        elif isinstance(event, AuthenticationFailedEvent):
            self.log_action(event.username, "AUTH_LOGIN_FAILED", event.reason)
        elif isinstance(event, LockdownTriggeredEvent):
            self.log_action("SYSTEM", "LOCKDOWN_TRIGGERED", f"Attempts: {event.failed_attempts} - {event.reason}")
        elif isinstance(event, LockdownClearedEvent):
            self.log_action(event.cleared_by, "LOCKDOWN_CLEARED", f"Unlocked by {event.cleared_by}")
        elif isinstance(event, UserRegisteredEvent):
            self.log_action(event.username, "USER_UPSERT", f"Role: {event.role}")
        elif isinstance(event, UserRemovedEvent):
            self.log_action(event.username, "USER_REMOVED", f"User {event.username} deleted")
        elif hasattr(event, "username"):
            self.log_action(getattr(event, "username", "SYSTEM"), event.__class__.__name__)

