# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import sqlite3
import sys
import tempfile

import pytest

# Ensure we're running from CARINA_CORE root and src/proto/ui are discoverable
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for _sub in ["", "src", "proto", "ui"]:
    _p = os.path.join(project_root, _sub) if _sub else project_root
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tests.memory_guard import (
    ProcessTreeRamGuard,
    apply_rlimit_data,
    configure_low_memory_env,
    parse_max_ram_mb,
    reclaim_test_resources,
)

configure_low_memory_env()

_SESSION_OUTPUT_TMPDIR = None
_SESSION_CONFIG_TMPDIR = None
_RAM_GUARD = None
_TEST_EXEC_COUNTER = 0

if not os.environ.get("CARINA_OUTPUT_DIR"):
    _SESSION_OUTPUT_TMPDIR = tempfile.TemporaryDirectory(prefix="carina_pytest_out_")
    os.environ["CARINA_OUTPUT_DIR"] = _SESSION_OUTPUT_TMPDIR.name

if not os.environ.get("CARINA_CONFIG_DIR"):
    _SESSION_CONFIG_TMPDIR = tempfile.TemporaryDirectory(prefix="carina_pytest_cfg_")
    os.environ["CARINA_CONFIG_DIR"] = _SESSION_CONFIG_TMPDIR.name

from launcher.env_setup import install_src_alias_finder

install_src_alias_finder(os.path.join(project_root, "src"))

from tests.mocks.system_mocks import install_slm_test_guard, install_system_mocks

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

install_slm_test_guard()

# Re-export fixtures for pytest discovery
from tests.fixtures.hardware_fixtures import mock_logger, mock_snmp_hardware


def pytest_addoption(parser):
    """Registers CARINA RAM-limiting options on the pytest CLI."""
    parser.addoption(
        "--max-ram-mb",
        action="store",
        type=int,
        default=None,
        help="Hard RSS/RLIMIT_DATA ceiling in MiB for the pytest process tree (0 disables; default: CARINA_PYTEST_MAX_RAM_MB or 2048).",
    )


def pytest_configure(config):
    """Initializes the process-tree RSS guard from CLI/environment settings."""
    global _RAM_GUARD
    max_ram_mb = parse_max_ram_mb(config.getoption("--max-ram-mb"))
    _RAM_GUARD = ProcessTreeRamGuard(max_ram_mb=max_ram_mb)


def pytest_sessionstart(session):
    """Starts the RSS watchdog thread and applies kernel RLIMIT_DATA."""
    if _RAM_GUARD is not None:
        _RAM_GUARD.start()
        _RAM_GUARD.rlimit_data_mb = apply_rlimit_data(_RAM_GUARD.max_ram_mb)


def pytest_runtest_logstart(nodeid, location):
    """Tracks the active test nodeid for RAM breach diagnostics."""
    if _RAM_GUARD is not None:
        _RAM_GUARD.current_nodeid = nodeid


def pytest_runtest_logfinish(nodeid, location):
    """Clears the active test nodeid after test completion."""
    if _RAM_GUARD is not None:
        _RAM_GUARD.current_nodeid = "<idle>"


def pytest_sessionfinish(session, exitstatus):
    """Stops the RSS watchdog, reclaims resources, and cleans session temp directories."""
    if _RAM_GUARD is not None:
        _RAM_GUARD.stop()
    reclaim_test_resources(force_gc=True)
    for tmpdir in (_SESSION_OUTPUT_TMPDIR, _SESSION_CONFIG_TMPDIR):
        if tmpdir is not None:
            try:
                tmpdir.cleanup()
            except Exception:
                pass


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Reports peak process-tree RSS against the configured RAM limit."""
    if _RAM_GUARD is not None:
        terminalreporter.write_line(_RAM_GUARD.format_summary())


def _clear_evp_registered_fleet() -> None:
    """Clears evp_registered_fleet efficiently in the isolated session test database."""
    db_type = os.environ.get("CARINA_DB_TYPE", "sqlite").strip().lower()
    if db_type == "sqlite":
        out_dir = os.environ.get("CARINA_OUTPUT_DIR", "").strip()
        if out_dir:
            db_path = os.path.join(out_dir, "results", "database", "carina_data.db")
            if not os.path.exists(db_path):
                return
            try:
                conn = sqlite3.connect(db_path)
                try:
                    conn.execute("DELETE FROM evp_registered_fleet;")
                    conn.commit()
                finally:
                    conn.close()
                return
            except Exception:
                pass

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


@pytest.fixture(autouse=True)
def setup_test_env():
    """
    Global fixture that runs before each test.
    Ensures that critical environment variables are configured for
    testing mode (avoiding real UI or production DB connections).
    """
    global _TEST_EXEC_COUNTER
    _prev_gateway_role = os.environ.get("CARINA_GATEWAY_ROLE")
    _prev_pythonpath = os.environ.get("PYTHONPATH")
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
    _clear_evp_registered_fleet()

    yield

    # Cleanup after test
    _clear_evp_registered_fleet()
    _TEST_EXEC_COUNTER += 1
    reclaim_test_resources(force_gc=(_TEST_EXEC_COUNTER % 25 == 0))

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

    if _prev_pythonpath is None:
        os.environ.pop("PYTHONPATH", None)
    else:
        os.environ["PYTHONPATH"] = _prev_pythonpath

    if _prev_gateway_role is None:
        os.environ.pop("CARINA_GATEWAY_ROLE", None)
    else:
        os.environ["CARINA_GATEWAY_ROLE"] = _prev_gateway_role
