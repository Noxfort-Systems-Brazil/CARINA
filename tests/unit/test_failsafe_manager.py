# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Unit tests for FailsafeManager transitions, incident reporting, and hardware dispatch."""

import time
from unittest.mock import MagicMock, patch

import pytest

from src.controller.failsafe_manager import FailsafeManager


def test_failsafe_manager_initial_state():
    mock_pipe = MagicMock()
    fm = FailsafeManager(ai_pipe_conn=mock_pipe)

    assert fm.current_operation_mode == "AUTOMATIC"
    assert fm.failsafe_active is False
    assert fm.check_synapse_health() is True
    assert fm.get_status()["operation_mode"] == "AUTOMATIC"


def test_failsafe_manager_trigger_and_recovery():
    mock_pipe = MagicMock()
    mock_monitor = MagicMock()
    on_trigger = MagicMock()
    on_recover = MagicMock()

    fm = FailsafeManager(
        ai_pipe_conn=mock_pipe,
        monitor_client=mock_monitor,
        on_failsafe_triggered=on_trigger,
        on_failsafe_recovered=on_recover,
    )
    fm.set_failsafe_timeout(0.1)

    # 1. Trigger failsafe
    with patch.object(fm, "_notify_hardware_failsafe") as mock_hw_failsafe:
        fm.trigger_failsafe()

        assert fm.failsafe_active is True
        assert fm.current_operation_mode == "WATCHDOG"
        mock_hw_failsafe.assert_called_once()
        on_trigger.assert_called_once()
        mock_monitor.report_incident.assert_called_once()

    # 2. Trigger again when already active (idempotent)
    with patch.object(fm, "_notify_hardware_failsafe") as mock_hw_failsafe:
        fm.trigger_failsafe()
        mock_hw_failsafe.assert_not_called()

    # 3. Attempt recovery
    with patch.object(fm, "_notify_hardware_recovery") as mock_hw_recovery:
        recovered = fm.attempt_recovery()

        assert recovered is True
        assert fm.failsafe_active is False
        assert fm.current_operation_mode == "AUTOMATIC"
        mock_hw_recovery.assert_called_once()
        on_recover.assert_called_once()
        mock_pipe.send.assert_called_with(("system", "wakeup", (), {}))

    # 4. Attempt recovery when not active (no-op)
    with patch.object(fm, "_notify_hardware_recovery") as mock_hw_recovery:
        recovered = fm.attempt_recovery()
        assert recovered is False
        mock_hw_recovery.assert_not_called()


def test_failsafe_manager_synapse_silence_detection():
    mock_pipe = MagicMock()
    fm = FailsafeManager(ai_pipe_conn=mock_pipe)
    fm.set_failsafe_timeout(0.05)

    # Initially before any frame arrives
    assert fm.check_synapse_health() is True

    # Frame arrives
    fm.record_frame_received()
    assert fm.check_synapse_health() is True

    # Sleep past timeout
    time.sleep(0.06)
    assert fm.check_synapse_health() is False
