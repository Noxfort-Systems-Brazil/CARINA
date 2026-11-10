# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Unit tests for src/watchdog/watchdog_process.py:
Tests run_watchdog process loop, message handling, config updates, FENIX notifications,
and graceful shutdown.
"""

import queue
from unittest.mock import MagicMock, patch
import pytest

from src.watchdog.watchdog_process import run_watchdog


class TestWatchdogProcess:
    @pytest.fixture
    def mock_locale(self):
        lm = MagicMock()
        lm.get_string.side_effect = lambda key, default=None, **kwargs: default or key
        return lm

    def test_run_watchdog_stop_signal_immediate(self, mock_locale):
        q = MagicMock()
        q.get_nowait.side_effect = ["STOP"]

        with (
            patch("os._exit") as mock_exit,
            patch("src.watchdog.watchdog_process.setup_logging"),
            patch("os.path.exists", return_value=False),
        ):
            run_watchdog(com_queue=q, locale_manager=mock_locale)
            mock_exit.assert_called_once_with(0)

    def test_run_watchdog_messages_and_config_update(self, mock_locale):
        q = MagicMock()
        # Drain receives HEARTBEAT, DNN_ERROR, CONFIG_UPDATE tuple, then STOP
        q.get_nowait.side_effect = [
            "HEARTBEAT",
            ("DNN_ERROR", "GradientExplosion"),
            ("CONFIG_UPDATE", 450),
            ("CONFIG_UPDATE", {"timeout_ms": 500}),
            ("CONFIG_UPDATE", {"heartbeat_timeout_seconds": "0.35"}),
            "STOP",
        ]

        with (
            patch("os._exit") as mock_exit,
            patch("src.watchdog.watchdog_process.setup_logging"),
            patch("os.path.exists", return_value=False),
            patch("src.fenix.fenix_supervisor.FenixSupervisor") as mock_fenix_cls,
        ):
            mock_fenix = MagicMock()
            mock_fenix_cls.return_value = mock_fenix

            run_watchdog(com_queue=q, locale_manager=mock_locale)
            assert mock_exit.called

    def test_run_watchdog_settings_file_read_and_error(self, mock_locale):
        q = MagicMock()
        q.get_nowait.side_effect = ["STOP"]

        # 1. Normal settings read
        with (
            patch("os._exit"),
            patch("src.watchdog.watchdog_process.setup_logging"),
            patch("os.path.exists", return_value=True),
            patch("configparser.ConfigParser.read"),
            patch("configparser.ConfigParser.getfloat", return_value=0.25),
        ):
            run_watchdog(com_queue=q, locale_manager=mock_locale)

        # 2. Corrupt settings file error
        q.get_nowait.side_effect = ["STOP"]
        with (
            patch("os._exit"),
            patch("src.watchdog.watchdog_process.setup_logging"),
            patch("os.path.exists", return_value=True),
            patch("configparser.ConfigParser.read", side_effect=ValueError("Corrupt ini")),
        ):
            run_watchdog(com_queue=q, locale_manager=mock_locale)

    def test_run_watchdog_wait_phase_messages_and_fenix_trigger(self, mock_locale):
        q = MagicMock()
        # Phase 1 empty, Phase 3 get(timeout=0.01) receives HEARTBEAT, then STOP
        q.get_nowait.side_effect = queue.Empty
        q.get.side_effect = [
            "HEARTBEAT",
            "DNN_ERROR",
            ("CONFIG_UPDATE", {"timeout_ms": 600}),
            "STOP",
        ]

        with (
            patch("os._exit"),
            patch("src.watchdog.watchdog_process.setup_logging"),
            patch("os.path.exists", return_value=False),
            patch("src.fenix.fenix_supervisor.FenixSupervisor") as mock_fenix_cls,
        ):
            run_watchdog(com_queue=q, locale_manager=mock_locale)

    def test_run_watchdog_keyboard_interrupt(self, mock_locale):
        q = MagicMock()
        q.get_nowait.side_effect = KeyboardInterrupt

        with (
            patch("os._exit") as mock_exit,
            patch("src.watchdog.watchdog_process.setup_logging"),
            patch("os.path.exists", return_value=False),
        ):
            run_watchdog(com_queue=q, locale_manager=mock_locale)
            mock_exit.assert_called_once_with(0)
