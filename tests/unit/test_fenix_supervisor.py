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

# File: tests/unit/test_fenix_supervisor.py
# Author: Gabriel Moraes
# Date: September 25, 2026

from unittest.mock import MagicMock

import pytest

from src.fenix.fenix_supervisor import FenixSupervisor
from src.fenix.protocols import FenixState, IProcessRunner, IRecoveryPolicy


def test_fenix_supervisor_lifecycle_and_resurrection():
    """Tests normal resurrection cycle of FenixSupervisor."""
    mock_runner = MagicMock(spec=IProcessRunner)
    mock_runner.pid = 98765
    mock_runner.is_alive = False
    mock_runner.spawn.return_value = True

    mock_policy = MagicMock(spec=IRecoveryPolicy)
    mock_policy.should_restart.return_value = True
    mock_policy.get_backoff_seconds.return_value = 0.001
    mock_policy.crash_count = 0

    states = []
    supervisor = FenixSupervisor(
        runner=mock_runner, recovery_policy=mock_policy, on_status_changed=lambda st, msg: states.append(st)
    )

    assert supervisor.state == FenixState.IDLE
    assert supervisor.child_pid == 98765

    # Resurrect
    success = supervisor.resurrect_ai(["test_cmd"])
    assert success is True
    assert supervisor.state == FenixState.FROZEN_SYNC
    assert FenixState.RESTARTING in states
    assert FenixState.FROZEN_SYNC in states
    mock_runner.spawn.assert_called_once()

    # Handover complete
    supervisor.confirm_handover_complete()
    assert supervisor.state == FenixState.NORMAL

    # Stop
    supervisor.stop()
    assert supervisor.state == FenixState.IDLE


def test_fenix_supervisor_halts_on_exceeded_crashes():
    """Tests that supervisor halts and remains in HALTED state if policy disallows restart."""
    mock_runner = MagicMock(spec=IProcessRunner)
    mock_policy = MagicMock(spec=IRecoveryPolicy)
    mock_policy.should_restart.return_value = False
    mock_policy.crash_count = 5

    supervisor = FenixSupervisor(runner=mock_runner, recovery_policy=mock_policy)

    success = supervisor.resurrect_ai()
    assert success is False
    assert supervisor.state == FenixState.HALTED
    mock_runner.spawn.assert_not_called()


def test_fenix_supervisor_records_crash():
    """Tests that recording child crash transitions state and updates policy."""
    mock_policy = MagicMock(spec=IRecoveryPolicy)
    supervisor = FenixSupervisor(recovery_policy=mock_policy)

    supervisor.record_child_crash(139)
    mock_policy.record_crash.assert_called_once_with(139)
    assert supervisor.state == FenixState.FAILSAFE_ACTIVE
