# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

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


def test_recovery_policy_exponential_backoff():
    """Verifies that exponential backoff scales with crash count up to max_backoff_seconds."""
    policy = WindowedCrashRecoveryPolicy(
        max_consecutive_crashes=5,
        crash_window_seconds=60.0,
        restart_backoff_seconds=1.5,
        exponential=True,
        max_backoff_seconds=10.0,
    )

    # 0 crashes -> base backoff
    assert policy.get_backoff_seconds() == 1.5

    # 1 crash -> base backoff (1.5 * 2^0 = 1.5)
    policy.record_crash(1)
    assert policy.get_backoff_seconds() == 1.5

    # 2 crashes -> 1.5 * 2^1 = 3.0s
    policy.record_crash(1)
    assert policy.get_backoff_seconds() == 3.0

    # 3 crashes -> 1.5 * 2^2 = 6.0s
    policy.record_crash(1)
    assert policy.get_backoff_seconds() == 6.0

    # 4 crashes -> 1.5 * 2^3 = 12.0s, capped at max_backoff_seconds (10.0s)
    policy.record_crash(1)
    assert policy.get_backoff_seconds() == 10.0

