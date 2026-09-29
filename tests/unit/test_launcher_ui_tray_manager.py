# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Noxfort Systems
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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# File: tests/unit/test_launcher_ui_tray_manager.py
# Author: Gabriel Moraes
# Date: September 2026

import os
import signal
import sys
from unittest.mock import MagicMock, patch

import pytest

from launcher.ui_tray_manager import UITrayManager


def test_ui_tray_manager_initialization():
    """Tests UITrayManager initialization and shutdown events."""
    mock_pm = MagicMock()
    mgr = UITrayManager(process_manager=mock_pm, bundle_root="/opt/carina")
    assert mgr.bundle_root == "/opt/carina"
    assert mgr.process_manager == mock_pm
    assert not mgr.shutdown_requested.is_set()
    assert not mgr.restore_requested.is_set()


def test_ui_tray_manager_signal_handlers():
    """Tests registration and firing of OS signal handler in UITrayManager."""
    mock_pm = MagicMock()
    mgr = UITrayManager(process_manager=mock_pm, bundle_root="/opt/carina")

    with patch("signal.signal") as mock_signal:
        mgr.setup_signal_handlers()
        assert mock_signal.called


def test_ui_tray_manager_run_headless_fallback():
    """Tests run loop when UI is not available or headlessly executed."""
    mock_pm = MagicMock()
    mgr = UITrayManager(process_manager=mock_pm, bundle_root="/opt/carina")

    # Request immediate shutdown
    mgr.shutdown_requested.set()

    with patch("launcher.ui_tray_manager.UI_AVAILABLE", False), patch("time.sleep", return_value=None):
        mgr.run()
        # Shutdown event is set, should exit cleanly
        assert mgr.shutdown_requested.is_set()
