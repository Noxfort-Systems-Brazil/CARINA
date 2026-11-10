# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

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

    # 3. Check health with no heartbeats -> triggers failsafe via timer (fixed-time only, no FENIX)
    assert wd.check_system_health() is False
    assert wd.is_in_failsafe is True
    on_activate.assert_called_once()
    on_fenix.assert_not_called()

    # 4. Register heartbeat -> recovers
    wd.register_heartbeat()
    assert wd.is_in_failsafe is False
    on_deactivate.assert_called_once()
    assert wd.check_system_health() is True

    # 5. Verify that a DNN error DOES trigger FENIX
    wd.trigger_dnn_error("Simulated DNN failure")
    assert wd.is_in_failsafe is True
    on_fenix.assert_called_once()


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
