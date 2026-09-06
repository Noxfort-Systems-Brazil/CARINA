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

# File: tests/unit/test_main_components.py
# Author: Gabriel Moraes
# Date: September 2026

import configparser
from unittest.mock import MagicMock

import pytest

from utils.hardware_initializer import HardwareInitializer
from utils.process_monitor import ProcessMonitor
from utils.settings_manager import SettingsManager


def test_hardware_initializer():
    """Verify HardwareInitializer environment setup and GPU detection."""
    logs = []

    def log_cb(msg, level="info"):
        logs.append((level, msg))

    HardwareInitializer.setup_environment(logging_func=log_cb)
    assert len(logs) == 1
    assert "TensorCores" in logs[0][1]

    gpu_info = HardwareInitializer.detect_gpu(logging_func=log_cb)
    assert isinstance(gpu_info, str)


def test_process_monitor():
    """Verify ProcessMonitor metrics manager initialization and background thread start."""
    pm = ProcessMonitor.start_background_monitor(process_name="Test_Process", port=8999)
    assert pm is not None
    assert "process_cpu_usage_percent" in pm.metrics
    assert "process_memory_usage_percent" in pm.metrics


def test_settings_manager_load_config():
    """Verify SettingsManager load_config returns a valid ConfigParser instance supporting .getint()."""
    sm = SettingsManager()
    cfg = sm.load_config()
    assert isinstance(cfg, configparser.ConfigParser)
    assert hasattr(cfg, "getint")
