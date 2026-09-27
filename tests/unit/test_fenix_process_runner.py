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

# File: tests/unit/test_fenix_process_runner.py
# Author: Gabriel Moraes
# Date: September 25, 2026

from unittest.mock import MagicMock, patch

import pytest

from src.fenix.process_runner import SubprocessRunner


def test_subprocess_runner_lifecycle():
    """Verifies that SubprocessRunner manages child processes and terminations correctly."""
    mock_popen = MagicMock()
    mock_popen.pid = 55555
    mock_popen.poll.return_value = None

    runner = SubprocessRunner()
    assert runner.is_alive is False
    assert runner.pid is None
    assert runner.poll() is None

    with patch("subprocess.Popen", return_value=mock_popen):
        success = runner.spawn(["python", "-m", "src.main"])
        assert success is True
        assert runner.is_alive is True
        assert runner.pid == 55555
        assert runner.poll() is None

        runner.terminate(timeout_seconds=0.1)
        mock_popen.terminate.assert_called_once()
        assert runner.is_alive is False


def test_subprocess_runner_spawn_failure():
    """Verifies that SubprocessRunner handles spawn exceptions gracefully."""
    runner = SubprocessRunner()

    with patch("subprocess.Popen", side_effect=OSError("Exec failed")):
        success = runner.spawn(["nonexistent_binary"])
        assert success is False
        assert runner.is_alive is False
        assert runner.pid is None
