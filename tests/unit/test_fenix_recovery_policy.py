# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
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

# File: tests/unit/test_fenix_recovery_policy.py
# Author: Gabriel Moraes
# Date: September 25, 2026

import pytest

from src.fenix.recovery_policy import WindowedCrashRecoveryPolicy


def test_recovery_policy_sliding_window_and_limits():
    """Verifies that WindowedCrashRecoveryPolicy tracks crashes and enforces limits within window."""
    current_time = 1000.0
    time_provider = lambda: current_time

    policy = WindowedCrashRecoveryPolicy(
        max_consecutive_crashes=2,
        crash_window_seconds=60.0,
        restart_backoff_seconds=2.0,
        time_provider=time_provider,
    )

    assert policy.crash_count == 0
    assert policy.should_restart() is True
    assert policy.get_backoff_seconds() == 2.0

    # Crash 1
    policy.record_crash(1)
    assert policy.crash_count == 1
    assert policy.should_restart() is True

    # Crash 2
    policy.record_crash(1)
    assert policy.crash_count == 2
    assert policy.should_restart() is True

    # Crash 3 -> Exceeds max 2 crashes in window
    policy.record_crash(1)
    assert policy.crash_count == 3
    assert policy.should_restart() is False

    # Advance time beyond sliding window (60s)
    current_time = 1061.0
    assert policy.crash_count == 0
    assert policy.should_restart() is True

    # Reset
    policy.record_crash(1)
    assert policy.crash_count == 1
    policy.reset()
    assert policy.crash_count == 0
