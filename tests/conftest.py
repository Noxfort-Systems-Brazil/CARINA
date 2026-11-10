# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import sys

import pytest

# Ensure we're running from CARINA_CORE root and src/proto/ui are discoverable
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for _sub in ["", "src", "proto", "ui"]:
    _p = os.path.join(project_root, _sub) if _sub else project_root
    if _p not in sys.path:
        sys.path.insert(0, _p)

from launcher.env_setup import install_src_alias_finder

install_src_alias_finder(os.path.join(project_root, "src"))

from tests.mocks.system_mocks import install_system_mocks

# --- MOCK HEAVY IMPORTS BEFORE THEY HAPPEN ---
from tests.mocks.torch_mock import DummyTensor, DummyTorch, install_dummy_torch

if os.environ.get("CARINA_USE_REAL_TORCH") != "1":
    install_dummy_torch()
    install_system_mocks()
else:
    # Running in real DL validation mode (if torch is installed)
    try:
        import torch  # noqa: F401
    except ImportError:
        install_dummy_torch()
        install_system_mocks()

# Re-export fixtures for pytest discovery
from tests.fixtures.hardware_fixtures import mock_logger, mock_snmp_hardware


@pytest.fixture(autouse=True)
def setup_test_env():
    """
    Global fixture that runs before each test.
    Ensures that critical environment variables are configured for
    testing mode (avoiding real UI or production DB connections).
    """
    os.environ["CARINA_TEST_MODE"] = "1"
    # Prevents PyQt/PySide interfaces from attempting to use X11 if running in headless CI
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["QT_MAC_WANTS_LAYER"] = "1"
    # Prevents OpenCV from attempting to open windows or connect to GTK/Wayland
    os.environ["OPENCV_VIDEOIO_PRIORITY_MSMF"] = "0"
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "dummy"
    # Torch JIT often crashes on initialization in headless environments
    os.environ["PYTORCH_JIT"] = "0"
    os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

    # Ensure EVP fleet table isolation across tests
    try:
        from src.database.db_engine import DatabaseEngine

        _eng = DatabaseEngine(locale_manager=None)
        _conn = _eng.get_connection()
        if _conn:
            with _conn.cursor() as _cur:
                _cur.execute("DELETE FROM evp_registered_fleet;")
            if hasattr(_conn, "commit"):
                _conn.commit()
            if hasattr(_conn, "close"):
                _conn.close()
    except Exception:
        pass

    yield

    # Cleanup after test
    try:
        from src.database.db_engine import DatabaseEngine

        _eng = DatabaseEngine(locale_manager=None)
        _conn = _eng.get_connection()
        if _conn:
            with _conn.cursor() as _cur:
                _cur.execute("DELETE FROM evp_registered_fleet;")
            if hasattr(_conn, "commit"):
                _conn.commit()
            if hasattr(_conn, "close"):
                _conn.close()
    except Exception:
        pass

    for key in [
        "CARINA_TEST_MODE",
        "QT_QPA_PLATFORM",
        "QT_MAC_WANTS_LAYER",
        "OPENCV_VIDEOIO_PRIORITY_MSMF",
        "OPENCV_FFMPEG_CAPTURE_OPTIONS",
        "PYTORCH_JIT",
        "TF_ENABLE_ONEDNN_OPTS",
    ]:
        os.environ.pop(key, None)
