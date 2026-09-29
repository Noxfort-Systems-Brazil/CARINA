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
#
# File: tests/conftest.py
# Author: Gabriel Moraes
# Date: 2026-04-16

import os
import sys

import pytest

# Ensure we're running from CARINA_CORE root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tests.mocks.system_mocks import install_system_mocks

# --- MOCK HEAVY IMPORTS BEFORE THEY HAPPEN ---
from tests.mocks.torch_mock import DummyTensor, DummyTorch, install_dummy_torch

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

    yield

    # Cleanup after test
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
