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

# File: tests/unit/test_launcher_process_manager.py
# Author: Gabriel Moraes
# Date: September 2026

import configparser
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

from launcher.process_manager import ProcessManager, run_controller_process


def test_process_manager_load_settings():
    """Tests loading and validation of settings.ini."""
    pm = ProcessManager()
    settings = pm.load_settings()
    assert isinstance(settings, configparser.ConfigParser)
    assert settings.has_section("TRAFFIC_RULES") or settings.has_section("DATABASE")


def test_process_manager_setup_queues_and_pipes():
    """Tests creation of IPC Pipes and Queues."""
    pm = ProcessManager()
    pm.setup_queues_and_pipes()

    assert pm.controller_conn is not None
    assert pm.ai_conn is not None
    expected_queues = [
        "wd",
        "sds",
        "sas",
        "ui",
        "db",
        "g_state",
        "g_signal",
        "sas_results",
        "mfd_results",
        "mfd_trigger",
        "ui_telemetry",
    ]
    for q_name in expected_queues:
        assert q_name in pm.queues
        assert hasattr(pm.queues[q_name], "put")


def test_process_manager_start_and_shutdown_all():
    """Tests starting all services and performing a graceful shutdown."""
    pm = ProcessManager()
    pm.settings = MagicMock()

    mock_process_instances = []

    def mock_process_factory(*args, **kwargs):
        mock_proc = MagicMock()
        mock_proc.name = kwargs.get("name", "mock_proc")
        mock_proc.pid = 9999
        mock_process_instances.append(mock_proc)
        return mock_proc

    with (
        patch("launcher.process_manager.Process", side_effect=mock_process_factory),
        patch("time.sleep", return_value=None),
        patch("src.drivers.go_gateway_client.GoGatewayClient.get_instance") as mock_go_client,
    ):

        pm.start_all_backend_services()

        # Check all processes were registered and started
        assert len(pm.processes) >= 6
        for p in pm.processes:
            assert p.start.called

        # Test graceful shutdown
        pm.controller_conn = MagicMock()
        pm.ai_conn = MagicMock()

        pm.shutdown_all()

        pm.controller_conn.send.assert_called_with(("system", "shutdown", (), {}))
        pm.ai_conn.send.assert_called_with(("system", "shutdown", (), {}))


def test_run_controller_process_shutdown():
    """Tests run_controller_process handling graceful shutdown and exit."""
    settings = MagicMock()
    pipe_conn = MagicMock()
    wd_q = MagicMock()
    sds_q = MagicMock()
    sas_q = MagicMock()
    ui_q = MagicMock()

    with (
        patch("launcher.process_manager.setup_logging"),
        patch("launcher.process_manager.ProcessMonitor.start_background_monitor"),
        patch("launcher.process_manager.CentralController") as mock_cc_cls,
        patch("os._exit") as mock_exit,
    ):

        mock_cc = MagicMock()
        mock_cc.run.side_effect = KeyboardInterrupt
        mock_cc_cls.return_value = mock_cc

        run_controller_process(settings, pipe_conn, wd_q, sds_q, sas_q, ui_q)
        mock_exit.assert_called_with(0)
