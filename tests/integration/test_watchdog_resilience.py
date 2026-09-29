# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

# File: tests/integration/test_watchdog_resilience.py
# Author: Gabriel Moraes
# Date: September 2026

import queue
import threading
import time
from unittest.mock import MagicMock

import pytest

from watchdog.watchdog_logic import Watchdog


@pytest.mark.integration
def test_watchdog_lifecycle_and_failsafe_transition():
    # Set grace period to 0.05s and timeout to 300ms (0.3s)
    wd = Watchdog(timeout_ms=300, grace_period_sec=0.05)

    on_activate = MagicMock()
    on_deactivate = MagicMock()
    on_fenix = MagicMock()
    wd.set_callbacks(on_activate, on_deactivate, on_fenix)

    # 1. During grace period, system is healthy
    assert wd.check_system_health() is True
    assert wd.is_in_failsafe is False

    # 2. Wait for grace period to expire
    time.sleep(0.06)

    # 3. Check health with no heartbeats -> triggers failsafe
    assert wd.check_system_health() is False
    assert wd.is_in_failsafe is True
    on_activate.assert_called_once()
    on_fenix.assert_called_once()

    # 4. Register heartbeat -> recovers
    wd.register_heartbeat()
    assert wd.is_in_failsafe is False
    on_deactivate.assert_called_once()
    assert wd.check_system_health() is True


@pytest.mark.integration
def test_watchdog_flapping_detection():
    wd = Watchdog(timeout_ms=300, grace_period_sec=0.0)

    # Simulate 5 consecutive triggers
    for i in range(5):
        # Force last heartbeat in past
        wd._startup_time = time.perf_counter() - 10.0
        wd._last_heartbeat_time = time.perf_counter() - 1.0
        wd.check_system_health()
        assert wd.is_in_failsafe is True
        # Recover
        wd.register_heartbeat()
        assert wd.is_in_failsafe is False

    assert wd._total_triggers == 5
    assert wd._total_recoveries == 5


@pytest.mark.integration
def test_watchdog_queue_consumer_simulation():
    # Simulate background queue processing
    msg_queue = queue.Queue()
    wd = Watchdog(timeout_ms=300, grace_period_sec=0.5)

    running = [True]

    def _worker():
        while running[0]:
            try:
                msg = msg_queue.get(timeout=0.02)
                if msg == "HEARTBEAT":
                    wd.register_heartbeat()
                elif msg == "STOP":
                    break
            except queue.Empty:
                pass
            wd.check_system_health()

    t = threading.Thread(target=_worker)
    t.start()

    try:
        # Send heartbeats
        for _ in range(5):
            msg_queue.put("HEARTBEAT")
            time.sleep(0.05)

        assert wd.is_in_failsafe is False
    finally:
        running[0] = False
        msg_queue.put("STOP")
        t.join(timeout=1.0)
