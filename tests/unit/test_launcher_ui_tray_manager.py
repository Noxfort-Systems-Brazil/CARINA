# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

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


def test_ui_tray_manager_handle_shutdown_signal():
    mock_pm = MagicMock()
    mgr = UITrayManager(process_manager=mock_pm, bundle_root="/opt/carina")

    captured_handler = None
    def mock_signal_reg(sig, handler):
        nonlocal captured_handler
        captured_handler = handler

    with patch("signal.signal", side_effect=mock_signal_reg):
        mgr.setup_signal_handlers()

    assert captured_handler is not None

    mock_ui_mod = MagicMock()
    mock_page = MagicMock()
    mock_page.window = MagicMock()
    mock_ui_mod.active_page = mock_page

    with patch.dict(sys.modules, {"ui.main_ui": mock_ui_mod}):
        with pytest.raises(KeyboardInterrupt):
            captured_handler(signal.SIGINT, None)

        assert mgr.shutdown_requested.is_set()
        assert mock_page.window.destroy.called


def test_ui_tray_manager_on_tray_restore():
    mgr = UITrayManager(process_manager=MagicMock(), bundle_root="/opt/carina")
    mgr.on_tray_restore()
    assert mgr.restore_requested.is_set()


def test_ui_tray_manager_on_tray_quit():
    mock_pm = MagicMock()
    mgr = UITrayManager(process_manager=mock_pm, bundle_root="/opt/carina")

    mock_proc = MagicMock()
    mock_child = MagicMock()
    mock_child.is_running.return_value = True
    mock_child.cmdline.return_value = ["python", "child_proc.py"]
    mock_proc.children.return_value = [mock_child]

    with patch("psutil.Process", return_value=mock_proc), \
         patch("os._exit") as mock_exit:
        mgr.on_tray_quit()

        assert mgr.shutdown_requested.is_set()
        assert mock_pm.shutdown_all.called
        assert mock_child.kill.called
        mock_exit.assert_called_once_with(0)


def test_ui_tray_manager_launch_flet_ui():
    mock_pm = MagicMock()
    mock_pm.queues = {"sas_results": MagicMock()}
    mgr = UITrayManager(process_manager=mock_pm, bundle_root="/opt/carina")

    with patch("flet.app") as mock_app:
        mgr.launch_flet_ui()
        assert mock_app.called

    # Error handling in ft.app
    with patch("flet.app", side_effect=RuntimeError("Flet UI crash")):
        mgr.launch_flet_ui()


def test_ui_tray_manager_run_with_tray(tmp_path):
    mock_pm = MagicMock()
    mgr = UITrayManager(process_manager=mock_pm, bundle_root=str(tmp_path))

    # Create dummy logo.png
    logo_dir = tmp_path / "ui" / "assets" / "images"
    logo_dir.mkdir(parents=True, exist_ok=True)
    (logo_dir / "logo.png").write_text("dummy")

    mock_tray = MagicMock()
    mock_tray.start.return_value = True

    # 1st launch: not shutdown, then restore requested, then shutdown
    call_count = 0
    def fake_launch():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            mgr.restore_requested.set()
        else:
            mgr.shutdown_requested.set()

    with patch("launcher.ui_tray_manager.UI_AVAILABLE", True), \
         patch("launcher.ui_tray_manager.TRAY_AVAILABLE", True), \
         patch("launcher.ui_tray_manager.TrayHandler", return_value=mock_tray), \
         patch.object(mgr, "launch_flet_ui", side_effect=fake_launch), \
         patch("time.sleep", return_value=None):

        mgr.run()

        assert call_count == 2
        assert mock_tray.stop.called

