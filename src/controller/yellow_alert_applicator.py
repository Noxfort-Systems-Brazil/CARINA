# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Actuates scheduled flashing yellow state transitions across override manager,
SUMO connection, and action supervisor. Decouples execution actuation from
YellowScheduleManager logic according to SRP and Clean Architecture.
"""

from typing import Any


class YellowAlertApplicator:
    """
    Handles hardware and simulator command actuation for yellow flashing schedules.
    """

    @staticmethod
    def apply_scheduled_alert(tl_id: str, mgr: Any, sumo_conn: Any, action_supervisor: Any) -> None:
        """Transitions a traffic light to ALERT (flashing yellow)."""
        payload = {"semaphore_id": tl_id, "state": "ALERT", "scheduled": True}
        if mgr and hasattr(mgr, "handle_ui_command"):
            mgr.handle_ui_command(payload, sumo_conn)
        elif mgr and hasattr(mgr, "active_overrides"):
            mgr.active_overrides[tl_id] = "ALERT"

        if action_supervisor and hasattr(action_supervisor, "apply_hardware_override"):
            action_supervisor.apply_hardware_override(tl_id, "ALERT")

    @staticmethod
    def revert_scheduled_alert(tl_id: str, mgr: Any, sumo_conn: Any, action_supervisor: Any) -> None:
        """Reverts a traffic light from ALERT back to NORMAL."""
        payload = {"semaphore_id": tl_id, "state": "NORMAL", "scheduled": True}
        if mgr and hasattr(mgr, "handle_ui_command"):
            mgr.handle_ui_command(payload, sumo_conn)
        elif mgr and hasattr(mgr, "active_overrides"):
            mgr.active_overrides.pop(tl_id, None)

        if action_supervisor and hasattr(action_supervisor, "apply_hardware_override"):
            action_supervisor.apply_hardware_override(tl_id, "NORMAL")
