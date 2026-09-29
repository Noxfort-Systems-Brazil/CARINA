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
# along with this program. If not, see <https://www.gnu.org/licenses/>.

# File: tests/unit/test_sas_helpers.py
# Author: Gabriel Moraes
# Date: September 2026

from datetime import datetime
from multiprocessing import Queue
from unittest.mock import MagicMock, patch

from sas.analyzer_data_processor import AnalyzerDataProcessor
from utils.locale_manager_backend import LocaleManagerBackend


def test_analyzer_data_processor_init():
    lm = MagicMock(spec=LocaleManagerBackend)
    processor = AnalyzerDataProcessor(lm)
    assert processor.locale_manager == lm
    assert processor.topology_parser is not None


def test_analyzer_engine_db_duration_validation(tmp_path):
    import configparser

    from sas.analyzer_engine import AnalyzerEngine

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
    from repositories.fluid_dynamics_repo import FluidDynamicsRepository

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


def test_infrastructure_analyzer_lightweight_cache():
    import configparser

    from analysis.infrastructure_analyzer import InfrastructureAnalyzer

    settings = configparser.ConfigParser()
    lm = MagicMock(spec=LocaleManagerBackend)
    lm.get_string.return_value = "mock_text"

    analyzer = InfrastructureAnalyzer(settings, lm)
    large_samples_list = [{"density": 0.1, "mean_speed": 10.0} for _ in range(500)]
    collected_data = {
        "j1": {
            "primary_edges": {"edge1": large_samples_list},
            "secondary_edges": {"edge2": large_samples_list},
            "conflict_events": 2,
            "type": "traffic_light",
        }
    }

    with (
        patch("analysis.infrastructure_analyzer.WarrantEvaluator") as mock_eval_cls,
        patch("analysis.infrastructure_analyzer.TextReportGenerator") as mock_rep_cls,
    ):
        mock_eval = MagicMock()
        mock_eval_cls.return_value = mock_eval
        mock_eval.evaluate.return_value = {
            "recommendation": "Keep",
            "current_status": "Existing",
            "justification": "Justified",
            "warrants": {},
            "data": {},
        }

        mock_rep = MagicMock()
        mock_rep_cls.return_value = mock_rep
        mock_rep.generate_txt_report.return_value = "report"

        res = analyzer.analyze_collected_data(
            collected_data=collected_data,
            last_analysis_cache={},
            scenario_name="test",
            true_traffic_light_ids=[],
        )

        cached_metrics = res["new_cache_data"]["junction_metrics"]
        assert "j1" in cached_metrics
        assert cached_metrics["j1"]["primary_edges"]["edge1"] == 500
        assert cached_metrics["j1"]["secondary_edges"]["edge2"] == 500
        assert cached_metrics["j1"]["conflict_events"] == 2
        assert cached_metrics["j1"]["type"] == "traffic_light"


def test_analyzer_data_processor_batch_processing():
    lm = MagicMock(spec=LocaleManagerBackend)
    processor = AnalyzerDataProcessor(lm)

    processor.topology_parser = MagicMock()
    processor.topology_parser.build.return_value = (
        {"j1": "traffic_light"},
        {"j1": {"edge1": {"num_lanes": 2, "length": 100.0}, "edge2": {"num_lanes": 1, "length": 100.0}}},
    )

    mock_db_mgr = MagicMock()

    def mock_batches(limit_seconds, batch_size):
        yield [
            {
                "edge_id": "edge1",
                "density": 10.0,
                "mean_speed": 15.0,
                "queue_length": 5,
                "edge_length": 100.0,
                "num_lanes": 2,
                "speed_limit": 20.0,
            },
            {
                "edge_id": "edge2",
                "density": 5.0,
                "mean_speed": 10.0,
                "queue_length": 2,
                "edge_length": 100.0,
                "num_lanes": 1,
                "speed_limit": 20.0,
            },
        ]
        yield [
            {
                "edge_id": "edge1",
                "density": 12.0,
                "mean_speed": 14.0,
                "queue_length": 8,
                "edge_length": 100.0,
                "num_lanes": 2,
                "speed_limit": 20.0,
            },
            {
                "edge_id": "edge2",
                "density": 6.0,
                "mean_speed": 9.0,
                "queue_length": 4,
                "edge_length": 100.0,
                "num_lanes": 1,
                "speed_limit": 20.0,
            },
        ]

    mock_db_mgr.query_fluid_dynamics_history_batches = mock_batches

    res, true_tls = processor.process_historical_data(mock_db_mgr, "mock.net.xml", limit_seconds=3600)

    assert "j1" in res
    assert "edge1" in res["j1"]["primary_edges"]
    assert "edge2" in res["j1"]["secondary_edges"]

    samples1 = res["j1"]["primary_edges"]["edge1"]
    assert len(samples1) == 100
    queues = [s["queue_length"] for s in samples1]
    assert 5 in queues


def test_analyzer_data_processor_equal_lanes():
    lm = MagicMock(spec=LocaleManagerBackend)
    processor = AnalyzerDataProcessor(lm)

    processor.topology_parser = MagicMock()
    processor.topology_parser.build.return_value = (
        {"j1": "traffic_light"},
        {
            "j1": {
                "edge1": {"num_lanes": 1, "length": 100.0, "lanes": ["edge1_0"]},
                "edge2": {"num_lanes": 1, "length": 100.0, "lanes": ["edge2_0"]},
                "edge3": {"num_lanes": 1, "length": 100.0, "lanes": ["edge3_0"]},
            }
        },
    )

    mock_db_mgr = MagicMock()

    def mock_batches(limit_seconds, batch_size):
        yield [
            {
                "edge_id": "edge1",
                "density": 20.0,
                "mean_speed": 15.0,
                "queue_length": 5,
                "edge_length": 100.0,
                "num_lanes": 1,
                "speed_limit": 20.0,
            },
            {
                "edge_id": "edge2",
                "density": 10.0,
                "mean_speed": 12.0,
                "queue_length": 2,
                "edge_length": 100.0,
                "num_lanes": 1,
                "speed_limit": 20.0,
            },
            {
                "edge_id": "edge3",
                "density": 5.0,
                "mean_speed": 10.0,
                "queue_length": 1,
                "edge_length": 100.0,
                "num_lanes": 1,
                "speed_limit": 20.0,
            },
        ]

    mock_db_mgr.query_fluid_dynamics_history_batches = mock_batches

    res, true_tls = processor.process_historical_data(mock_db_mgr, "mock.net.xml", limit_seconds=3600)

    assert "j1" in res
    assert "edge1" in res["j1"]["primary_edges"]
    assert "edge2" in res["j1"]["primary_edges"]
    assert "edge3" in res["j1"]["secondary_edges"]
    assert "edge1" not in res["j1"]["secondary_edges"]
    assert "edge3" not in res["j1"]["primary_edges"]


def test_analyzer_data_processor_accumulated_equal_lanes():
    lm = MagicMock(spec=LocaleManagerBackend)
    processor = AnalyzerDataProcessor(lm)

    processor.topology_parser = MagicMock()
    processor.topology_parser.build.return_value = (
        {"j1": "traffic_light"},
        {
            "j1": {
                "edge1": {"num_lanes": 1, "length": 100.0, "lanes": ["edge1_0"]},
                "edge2": {"num_lanes": 1, "length": 100.0, "lanes": ["edge2_0"]},
                "edge3": {"num_lanes": 1, "length": 100.0, "lanes": ["edge3_0"]},
            }
        },
    )

    accumulated_data = {
        "total_vehicles_departed_per_lane": {"edge1_0": 100, "edge2_0": 50, "edge3_0": 10},
        "total_waiting_time_per_lane": {"edge1_0": 1000.0, "edge2_0": 500.0, "edge3_0": 200.0},
        "conflict_events_per_junction": {"j1": 3},
    }

    res, true_tls = processor.process_accumulated_data(accumulated_data, 3600.0, "mock.net.xml")

    assert "j1" in res
    assert res["j1"]["volume"] == 150
    assert res["j1"]["vol_secondary"] == 10
    assert res["j1"]["avg_delay"] == 20.0
