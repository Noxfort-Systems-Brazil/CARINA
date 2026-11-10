# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Unit tests for MultiprocessingProcessRunner and FenixSupervisor integration."""

from unittest.mock import MagicMock

import pytest

from src.fenix.fenix_supervisor import FenixSupervisor
from src.fenix.multiprocessing_runner import MultiprocessingProcessRunner
from src.fenix.protocols import FenixState, IRecoveryPolicy


def test_multiprocessing_runner_lifecycle():
    mock_proc = MagicMock()
    mock_proc.pid = 43210
    # Process is alive initially, then exits after terminate
    mock_proc.is_alive.side_effect = [True, True, False, True, False]

    runner = MultiprocessingProcessRunner(target=lambda: None, args=(), name="TestProcess")
    runner.set_process(mock_proc)

    assert runner.pid == 43210
    assert runner.is_alive is True

    # Terminate (exits cleanly before kill fallback)
    success = runner.terminate(timeout_sec=0.1)
    assert success is True
    mock_proc.terminate.assert_called_once()
    mock_proc.kill.assert_not_called()

    # Kill
    success = runner.kill()
    assert success is True
    mock_proc.kill.assert_called_once()


def test_fenix_supervisor_with_multiprocessing_runner():
    mock_runner = MagicMock(spec=MultiprocessingProcessRunner)
    mock_runner.pid = 55555
    mock_runner.is_alive = False
    mock_runner.spawn.return_value = True

    mock_policy = MagicMock(spec=IRecoveryPolicy)
    mock_policy.should_restart.return_value = True
    mock_policy.get_backoff_seconds.return_value = 0.001
    mock_policy.crash_count = 0

    supervisor = FenixSupervisor(runner=mock_runner, recovery_policy=mock_policy)

    assert supervisor.state == FenixState.IDLE
    assert supervisor.child_pid == 55555

    resurrected = supervisor.resurrect_ai()
    assert resurrected is True
    assert supervisor.state == FenixState.FROZEN_SYNC
    mock_runner.spawn.assert_called_once()

    supervisor.confirm_handover_complete()
    assert supervisor.state == FenixState.NORMAL


def test_multiprocessing_runner_terminate_timeout_seconds():
    """Verifies that terminate accepts timeout_seconds keyword without error."""
    mock_proc = MagicMock()
    mock_proc.pid = 11111
    mock_proc.is_alive.side_effect = [True, False]

    runner = MultiprocessingProcessRunner(name="TestProcess")
    runner.set_process(mock_proc)

    # Calling with timeout_seconds (as invoked by FenixSupervisor) must succeed
    success = runner.terminate(timeout_seconds=0.5)
    assert success is True
    mock_proc.terminate.assert_called_once()
    mock_proc.join.assert_called_once_with(timeout=0.5)


def test_multiprocessing_runner_poll():
    """Verifies that poll returns None when process is active, and exitcode when terminated."""
    mock_proc = MagicMock()
    mock_proc.exitcode = None

    runner = MultiprocessingProcessRunner(name="TestProcess")
    assert runner.poll() is None

    runner.set_process(mock_proc)
    assert runner.poll() is None

    mock_proc.exitcode = 0
    assert runner.poll() == 0

    mock_proc.exitcode = 137
    assert runner.poll() == 137

