# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
YellowScheduleManager: Coordinates scheduled flashing yellow (amarelo intermitente)
for traffic lights based on configured time windows (e.g. late night hours).
Complies with Single Responsibility Principle (SRP) and Open/Closed Principle (OCP).
"""

from datetime import datetime, time
import logging
from typing import Any, Dict, List, Optional, Set

from src.controller.yellow_alert_applicator import YellowAlertApplicator

logger = logging.getLogger(__name__)


class YellowScheduleManager:
    """
    Manages the lifecycle and execution of time-of-day yellow flashing schedules.
    Automatically transitions target traffic lights to ALERT (flashing yellow) during
    the configured window and restores them to NORMAL afterwards.
    """

    def __init__(
        self,
        settings_dict: Optional[Dict[str, Any]] = None,
        override_manager: Optional[Any] = None,
        locale_manager: Optional[Any] = None,
        sds_data_queue: Optional[Any] = None,
    ):
        self.override_manager = override_manager
        self.locale_manager = locale_manager
        self.sds_data_queue = sds_data_queue

        # Schedule parameters
        self.enabled: bool = False
        self.start_time: time = time(23, 0)
        self.end_time: time = time(5, 0)
        self.all_semaphores: bool = False
        self.semaphores: Set[str] = set()

        # State tracking: semaphores that were placed in ALERT by this schedule
        self.active_scheduled_semaphores: Set[str] = set()
        self._last_tick_time: Optional[datetime] = None

        if settings_dict:
            self.load_config(settings_dict)

    @staticmethod
    def parse_time_str(time_str: Any, default: time) -> time:
        """Parses a time string in HH:MM or HH:MM:SS format to datetime.time."""
        if isinstance(time_str, time):
            return time_str
        if not time_str or not isinstance(time_str, str):
            return default

        parts = time_str.strip().split(":")
        try:
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 else 0
            second = int(parts[2]) if len(parts) > 2 else 0
            return time(hour, minute, second)
        except (ValueError, IndexError):
            logger.warning(f"[YellowScheduleManager] Invalid time format '{time_str}', using fallback {default}")
            return default

    @staticmethod
    def is_time_in_window(start: time, end: time, check_time: time) -> bool:
        """
        Determines whether check_time falls within [start, end).
        Handles midnight crossings (e.g. 23:00 to 05:00) deterministically.
        """
        if start == end:
            return False
        if start < end:
            return start <= check_time < end
        else:
            return check_time >= start or check_time < end

    def load_config(self, config: Dict[str, Any]) -> None:
        """Loads schedule settings from a dictionary."""
        enabled_val = config.get("yellow_schedule_enabled", False)
        if isinstance(enabled_val, str):
            self.enabled = enabled_val.strip().lower() in ("true", "1", "yes", "on")
        else:
            self.enabled = bool(enabled_val)

        start_val = config.get("yellow_schedule_start", "23:00")
        end_val = config.get("yellow_schedule_end", "05:00")
        self.start_time = self.parse_time_str(start_val, time(23, 0))
        self.end_time = self.parse_time_str(end_val, time(5, 0))

        all_sem_val = config.get("yellow_schedule_all_semaphores", False)
        if isinstance(all_sem_val, str):
            self.all_semaphores = all_sem_val.strip().lower() in ("true", "1", "yes", "on")
        else:
            self.all_semaphores = bool(all_sem_val)

        raw_semaphores = config.get("yellow_schedule_semaphores", "")
        self.semaphores = self._parse_semaphores_set(raw_semaphores)

        current_summary = (
            self.enabled,
            self.start_time,
            self.end_time,
            self.all_semaphores,
            tuple(sorted(list(self.semaphores))),
        )
        if getattr(self, "_last_logged_config", None) != current_summary:
            self._last_logged_config = current_summary
            logger.info(
                f"[YellowScheduleManager] Config loaded: enabled={self.enabled}, "
                f"window={self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')}, "
                f"all_semaphores={self.all_semaphores}, semaphores={sorted(list(self.semaphores))}"
            )

    @staticmethod
    def _parse_semaphores_set(raw: Any) -> Set[str]:
        if isinstance(raw, (set, list, tuple)):
            return {str(s).strip() for s in raw if str(s).strip()}
        if isinstance(raw, str):
            return {s.strip() for s in raw.split(",") if s.strip()}
        return set()

    def is_active_now(self, check_time: Optional[time] = None) -> bool:
        """Returns True if the schedule is currently enabled and within the time window."""
        if not self.enabled:
            return False
        current = check_time or datetime.now().time()
        return self.is_time_in_window(self.start_time, self.end_time, current)

    def is_semaphore_scheduled(self, semaphore_id: str) -> bool:
        """Returns True if the given semaphore ID is targeted by the schedule."""
        if not semaphore_id:
            return False
        if self.all_semaphores:
            return True
        return semaphore_id in self.semaphores

    def is_semaphore_active_now(self, semaphore_id: str, check_time: Optional[time] = None) -> bool:
        """Returns True if this semaphore should be in flashing yellow right now."""
        return self.is_active_now(check_time) and self.is_semaphore_scheduled(semaphore_id)

    def add_semaphore(self, semaphore_id: str) -> None:
        """Adds a semaphore to the target schedule list."""
        if semaphore_id:
            self.semaphores.add(semaphore_id.strip())

    def remove_semaphore(self, semaphore_id: str) -> None:
        """Removes a semaphore from the target schedule list."""
        if semaphore_id:
            self.semaphores.discard(semaphore_id.strip())

    def toggle_semaphore(self, semaphore_id: str) -> bool:
        """Toggles inclusion of a semaphore in the schedule. Returns True if now included."""
        sid = semaphore_id.strip() if semaphore_id else ""
        if not sid:
            return False
        if sid in self.semaphores:
            self.semaphores.remove(sid)
            return False
        self.semaphores.add(sid)
        return True

    def get_target_semaphores(self) -> List[str]:
        """Resolves list of all targeted semaphore IDs."""
        if not self.all_semaphores:
            return sorted(list(self.semaphores))

        try:
            from src.controller.map_discoverer import MapTopologyDiscoverer

            discovered = MapTopologyDiscoverer.discover_intersections()
            if discovered:
                return sorted(discovered)
        except Exception as _exc:
            logger.debug("[controller] Ignored recoverable error: %s", _exc)

        if self.override_manager and hasattr(self.override_manager, "active_overrides"):
            return sorted(list(set(self.override_manager.active_overrides.keys()).union(self.semaphores)))

        return sorted(list(self.semaphores))

    def tick(
        self,
        override_manager: Optional[Any] = None,
        sumo_conn: Optional[Any] = None,
        action_supervisor: Optional[Any] = None,
        current_time: Optional[time] = None,
    ) -> Dict[str, Any]:
        """
        Executes a periodic schedule evaluation cycle.
        Applies ALERT when inside window, and reverts to NORMAL when window expires.
        """
        mgr = override_manager or self.override_manager
        now_time = current_time or datetime.now().time()
        is_active = self.is_active_now(now_time)

        changes = {"activated": [], "restored": []}

        if is_active:
            target_ids = self.get_target_semaphores()
            for tl_id in target_ids:
                if tl_id not in self.active_scheduled_semaphores:
                    self._apply_scheduled_alert(tl_id, mgr, sumo_conn, action_supervisor)
                    self.active_scheduled_semaphores.add(tl_id)
                    changes["activated"].append(tl_id)
                    logger.info(
                        f"[YellowScheduleManager] Semaphore '{tl_id}' switched to SCHEDULED FLASHING YELLOW "
                        f"({self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')})."
                    )
        else:
            to_restore = list(self.active_scheduled_semaphores)
            for tl_id in to_restore:
                self._revert_scheduled_alert(tl_id, mgr, sumo_conn, action_supervisor)
                self.active_scheduled_semaphores.discard(tl_id)
                changes["restored"].append(tl_id)
                logger.info(
                    f"[YellowScheduleManager] Semaphore '{tl_id}' restored to NORMAL "
                    f"(Schedule window ended)."
                )

        return changes

    def _apply_scheduled_alert(self, tl_id: str, mgr: Any, sumo_conn: Any, action_supervisor: Any) -> None:
        YellowAlertApplicator.apply_scheduled_alert(tl_id, mgr, sumo_conn, action_supervisor)

    def _revert_scheduled_alert(self, tl_id: str, mgr: Any, sumo_conn: Any, action_supervisor: Any) -> None:
        YellowAlertApplicator.revert_scheduled_alert(tl_id, mgr, sumo_conn, action_supervisor)

    def get_status(self) -> Dict[str, Any]:
        """Returns the current state and parameters of the schedule manager."""
        return {
            "enabled": self.enabled,
            "start_time": self.start_time.strftime("%H:%M"),
            "end_time": self.end_time.strftime("%H:%M"),
            "all_semaphores": self.all_semaphores,
            "semaphores": sorted(list(self.semaphores)),
            "is_window_active": self.is_active_now(),
            "active_scheduled_count": len(self.active_scheduled_semaphores),
            "active_scheduled_list": sorted(list(self.active_scheduled_semaphores)),
        }
