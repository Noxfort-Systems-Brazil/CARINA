# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import time

import pytest

from src.watchdog.watchdog_logic import Watchdog


@pytest.fixture
def watchdog_instance():
    """
    Creates an isolated instance of the Watchdog (Safety).
    """
    # Create the instance setting 500ms of timeout and 0.0s grace period for instant test triggers
    wd = Watchdog(timeout_ms=500, grace_period_sec=0.0)
    return wd


@pytest.mark.unit
def test_watchdog_healthy_pulse(watchdog_instance):
    """
    Tests if sending constant pulses prevents the security trigger.
    """
    wd = watchdog_instance

    # Register the manual heartbeat (simulating Synapse)
    wd.register_heartbeat()
    time.sleep(0.1)

    # Verify system health
    is_healthy = wd.check_system_health()

    assert is_healthy is True
    assert wd.is_in_failsafe is False


@pytest.mark.unit
def test_watchdog_timeout_trigger(watchdog_instance):
    """
    Simulates a delay greater than timeout_ms and verifies if failsafe is activated.
    """
    wd = watchdog_instance

    # Register base heartbeat and artificially delay it
    wd.register_heartbeat()
    wd._last_heartbeat_time = time.perf_counter() - 0.6  # 600ms gap

    # The check must return False and activate Failsafe
    is_healthy = wd.check_system_health()

    assert is_healthy is False
    assert wd.is_in_failsafe is True


@pytest.mark.unit
def test_watchdog_recovery(watchdog_instance):
    """
    Tests if the Watchdog can recover after entering Failsafe.
    """
    wd = watchdog_instance
    wd._last_heartbeat_time = time.perf_counter() - 0.6
    wd.check_system_health()
    assert wd.is_in_failsafe is True

    # New heartbeat must reset the system
    wd.register_heartbeat()
    assert wd.is_in_failsafe is False


@pytest.mark.unit
def test_watchdog_update_timeout(watchdog_instance):
    """
    Tests dynamic timeout reconfiguration and 300ms safety floor enforcement.
    """
    wd = watchdog_instance
    wd.update_timeout(800)
    assert wd._timeout_seconds == pytest.approx(0.8)

    # Below 300ms floor should clamp to 300ms (0.3s)
    wd.update_timeout(100)
    assert wd._timeout_seconds == pytest.approx(0.3)

