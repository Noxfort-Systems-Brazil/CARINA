# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: tests/unit/test_analysis_orchestrator.py
# Author: Gabriel Moraes
# Date: September 2026

import configparser
from multiprocessing import Queue
from unittest.mock import MagicMock, patch

from sas.analysis_orchestrator import AnalysisOrchestrator
from utils.locale_manager_backend import LocaleManagerBackend


def test_analysis_orchestrator_hft_rich_update():
    sas_queue = Queue()
    db_queue = Queue()
    settings = configparser.ConfigParser()
    settings["ANALYSIS_SCHEDULE"] = {
        "analysis_interval_value": "1",
        "analysis_interval_unit": "days",
    }

    lm = MagicMock(spec=LocaleManagerBackend)
    lm.get_string.return_value = "mocked_string"

    with patch("sas.analysis_orchestrator.DatabaseManager") as mock_db_mgr_cls:
        mock_db_mgr = MagicMock()
        mock_db_mgr_cls.return_value = mock_db_mgr

        orchestrator = AnalysisOrchestrator(sas_queue, settings, db_queue, lm)
        orchestrator.initial_delay = 10
        orchestrator.frequency = 60
        orchestrator.engine = MagicMock()

        with patch("os.path.exists", return_value=True), patch("os.listdir", return_value=["test.net.xml"]):
            hft_packet = ("hft_rich_update", {"sim_time": 5})
            sas_queue.put(hft_packet)
            sas_queue.put(None)

            orchestrator.run()
            orchestrator.engine.run_analysis.assert_not_called()

            sas_queue.put(("hft_rich_update", {"sim_time": 75}))
            sas_queue.put(None)

            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.fetchone.return_value = (42,)
            mock_db_mgr.engine.get_connection.return_value = mock_conn
            mock_db_mgr.engine.db_type = "sqlite"

            orchestrator.run()

            orchestrator.engine.run_analysis.assert_called_once()
            args, kwargs = orchestrator.engine.run_analysis.call_args
            assert kwargs["sim_duration"] == 75
            assert kwargs["scenario_name"] == "hft_live_session"
            assert kwargs["run_id"] == 42
            assert kwargs["db_manager"] == mock_db_mgr


def test_analysis_orchestrator_trigger_analysis():
    sas_queue = Queue()
    db_queue = Queue()
    settings = configparser.ConfigParser()
    settings["ANALYSIS_SCHEDULE"] = {
        "analysis_interval_value": "1",
        "analysis_interval_unit": "days",
    }

    lm = MagicMock(spec=LocaleManagerBackend)
    lm.get_string.return_value = "mocked_string"

    with patch("sas.analysis_orchestrator.DatabaseManager") as mock_db_mgr_cls:
        mock_db_mgr = MagicMock()
        mock_db_mgr_cls.return_value = mock_db_mgr

        orchestrator = AnalysisOrchestrator(sas_queue, settings, db_queue, lm)
        orchestrator.last_net_file_path = "mock.net.xml"
        orchestrator.last_sim_time = 500
        orchestrator.engine = MagicMock()

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (100,)
        mock_db_mgr.engine.get_connection.return_value = mock_conn
        mock_db_mgr.engine.db_type = "sqlite"

        sas_queue.put(("trigger_analysis", {}))
        sas_queue.put(None)

        orchestrator.run()

        orchestrator.engine.run_analysis.assert_called_once()
        args, kwargs = orchestrator.engine.run_analysis.call_args
        assert kwargs["scenario_name"] == "hft_live_session"
        assert kwargs["net_file_path"] == "mock.net.xml"
        assert kwargs["run_id"] == 100
        assert kwargs["sim_duration"] == 500
        assert kwargs["db_manager"] == mock_db_mgr
