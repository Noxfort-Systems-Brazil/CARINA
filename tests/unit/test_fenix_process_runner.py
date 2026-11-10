# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

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
