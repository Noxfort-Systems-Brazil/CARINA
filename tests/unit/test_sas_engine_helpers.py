# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import configparser
from datetime import datetime
from multiprocessing import Queue
from unittest.mock import MagicMock, patch

from repositories.fluid_dynamics_repo import FluidDynamicsRepository
from sas.analyzer_engine import AnalyzerEngine
from utils.locale_manager_backend import LocaleManagerBackend


def test_analyzer_engine_db_duration_validation(tmp_path):
    settings = configparser.ConfigParser()
    settings["ANALYSIS_SCHEDULE"] = {
        "analysis_interval_value": "2",
        "analysis_interval_unit": "hours",
    }

    db_queue = Queue()
    lm = MagicMock(spec=LocaleManagerBackend)
    lm.get_string.return_value = "Skipped"

    mock_db_mgr = MagicMock()
    mock_db_mgr.get_fluid_dynamics_time_range.return_value = 0.0

    sas_queue = Queue()
    engine = AnalyzerEngine(settings, db_queue, lm, sas_result_queue=sas_queue)

    with patch("src.utils.paths.get_base_output_dir", return_value=str(tmp_path)):
        engine.run_analysis(
            accumulated_data={},
            sim_duration=10,
            scenario_name="test_scenario",
            net_file_path="mock.net.xml",
            run_id=1,
            db_manager=mock_db_mgr,
        )

        status_data = sas_queue.get(timeout=1.0)
        assert status_data["status"] == "error"
        assert "Nenhum dado de tráfego disponível" in status_data["message"]


def test_query_fluid_dynamics_history_with_limit():
    mock_engine = MagicMock()
    mock_engine.db_type = "postgres"
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_engine.get_connection.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchone.return_value = (datetime.now(),)
    mock_cursor.fetchall.return_value = []

    lm = MagicMock(spec=LocaleManagerBackend)
    repo = FluidDynamicsRepository(mock_engine, lm)

    repo.query_fluid_dynamics_history(limit_seconds=3600)
    assert mock_cursor.execute.call_count == 2
    sql_call = mock_cursor.execute.call_args_list[-1][0][0]
    assert "WHERE collected_at >= %s" in sql_call

    mock_engine.db_type = "sqlite"
    mock_cursor.reset_mock()
    repo.query_fluid_dynamics_history(limit_seconds=3600)
    assert mock_cursor.execute.call_count == 2
    sql_call = mock_cursor.execute.call_args_list[-1][0][0]
    assert "WHERE collected_at >= ?" in sql_call
