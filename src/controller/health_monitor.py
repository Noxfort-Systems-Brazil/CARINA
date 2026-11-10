# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend


class AIHealthMonitor:
    """Monitors the 'pulse' of the AI process to detect failures."""

    def __init__(self, heartbeat_timeout: float, locale_manager: "LocaleManagerBackend"):
        """
        Initializes the health monitor.
        """
        self.timeout = heartbeat_timeout
        self.locale_manager = locale_manager
        lm = self.locale_manager

        self.last_message_time = None
        self.is_healthy = True

        logging.info(lm.get_string("health_monitor.init.monitor_created", timeout=self.timeout))
        self.record_activity()

    def record_activity(self):
        """
        Records that the AI sent a message, resetting the heartbeat timer.
        """
        self.last_message_time = time.time()
        if not self.is_healthy:
            logging.info(self.locale_manager.get_string("health_monitor.activity.communication_reestablished"))
            self.is_healthy = True

    def check_health(self) -> bool:
        """
        Checks if the AI has exceeded the response timeout.
        Returns the current health status.
        """
        lm = self.locale_manager
        if not self.is_healthy:
            return False

        elapsed_time = time.time() - self.last_message_time
        if elapsed_time > self.timeout:
            logging.critical(lm.get_string("health_monitor.health_check.failure", timeout=f"{self.timeout:.2f}"))
            logging.warning(lm.get_string("health_monitor.health_check.switching_to_watchdog"))
            self.is_healthy = False

        return self.is_healthy
