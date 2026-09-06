# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# File: tests/unit/test_window_manager.py
# Author: Gabriel Moraes
# Date: September 2026

import threading
from unittest.mock import MagicMock

import pytest

from ui.managers.window_manager import WindowManager


def test_window_close_minimizes_to_tray():
    """Verify clicking 'X' (e.data == 'close') minimizes and hides window instead of quitting."""
    mock_page = MagicMock()
    mock_window = MagicMock()
    mock_page.window = mock_window
    mock_page.run_thread = MagicMock()

    restore_event = threading.Event()
    shutdown_event = threading.Event()

    wm = WindowManager(mock_page, restore_event=restore_event, shutdown_event=shutdown_event)
    wm.configure_window(app_title="CARINA Test")

    # Simulate user clicking 'X' on window titlebar
    mock_event = MagicMock()
    mock_event.data = "close"
    wm._window_event(mock_event)

    # Verify shutdown event was NOT set
    assert not shutdown_event.is_set()

    # Verify window was minimized and hidden
    assert mock_window.minimized is True
    assert mock_window.visible is False
    assert mock_page.update.called


def test_restore_window():
    """Verify _restore_window brings hidden/minimized window back to front."""
    mock_page = MagicMock()
    mock_window = MagicMock()
    mock_window.visible = False
    mock_window.minimized = True
    mock_page.window = mock_window

    restore_event = threading.Event()
    shutdown_event = threading.Event()

    wm = WindowManager(mock_page, restore_event=restore_event, shutdown_event=shutdown_event)

    wm._restore_window()

    assert mock_window.visible is True
    assert mock_window.minimized is False
    assert mock_window.focused is True
    assert mock_window.to_front.called
    assert mock_page.update.called
