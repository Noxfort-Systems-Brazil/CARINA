# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import configparser
from datetime import datetime
from unittest.mock import MagicMock, patch
import pytest

from src.sas.analyzer_engine import AnalyzerEngine


@pytest.fixture
def base_analyzer():
    settings = configparser.ConfigParser()
    settings.add_section("ANALYSIS_SCHEDULE")
    settings.set("ANALYSIS_SCHEDULE", "analysis_interval_value", "2")
    settings.set("ANALYSIS_SCHEDULE", "analysis_interval_unit", "weeks")

    db_queue = MagicMock()
    sas_queue = MagicMock()
    lm = MagicMock()
    lm.get_string.side_effect = lambda k, **kw: f"mock_{k}"

    engine = AnalyzerEngine(
        settings=settings,
        db_data_queue=db_queue,
        locale_manager=lm,
        sas_result_queue=sas_queue,
    )
    return engine, settings, db_queue, sas_queue, lm


def test_analyzer_engine_get_required_seconds(base_analyzer):
    engine, settings, _, _, _ = base_analyzer

    # 2 weeks = 2 * 604800 = 1209600
    assert engine._get_required_seconds() == 1209600

    # Test invalid unit fallback
    settings.set("ANALYSIS_SCHEDULE", "analysis_interval_unit", "invalid")
    assert engine._get_required_seconds() == 2 * 86400

    # Test error parsing fallback
    settings.remove_section("ANALYSIS_SCHEDULE")
    assert engine._get_required_seconds() == 7 * 86400


def test_analyzer_engine_run_analysis_skipped_no_data(base_analyzer, tmp_path):
    engine, _, _, sas_queue, _ = base_analyzer

    with patch("src.utils.paths.get_base_output_dir", return_value=str(tmp_path)):
        # Duration <= 0
        engine.run_analysis(
            accumulated_data={},
            sim_duration=0.0,
            scenario_name="scen_1",
            net_file_path="",
            run_id=1,
            db_manager=MagicMock(),
        )
        assert sas_queue.put.called
        assert sas_queue.put.call_args[0][0]["status"] == "error"


def test_analyzer_engine_run_analysis_no_db_data_and_empty_accumulated(base_analyzer, tmp_path):
    engine, _, _, sas_queue, _ = base_analyzer

    mock_db = MagicMock()
    mock_db.get_fluid_dynamics_time_range.return_value = 0.0

    with patch("src.utils.paths.get_base_output_dir", return_value=str(tmp_path)):
        engine.run_analysis(
            accumulated_data={},
            sim_duration=100.0,
            scenario_name="scen_1",
            net_file_path="mock.net.xml",
            run_id=1,
            db_manager=mock_db,
        )
        assert sas_queue.put.called
        assert sas_queue.put.call_args[0][0]["status"] == "error"


def test_analyzer_engine_run_analysis_processor_no_data(base_analyzer, tmp_path):
    engine, _, _, sas_queue, _ = base_analyzer

    mock_db = MagicMock()
    mock_db.get_fluid_dynamics_time_range.return_value = 3600.0

    with patch("src.utils.paths.get_base_output_dir", return_value=str(tmp_path)), \
         patch("src.sas.analyzer_engine.AnalyzerDataProcessor") as MockProc:
        mock_proc_instance = MagicMock()
        mock_proc_instance.process_historical_data.return_value = ({}, [])
        MockProc.return_value = mock_proc_instance

        engine.run_analysis(
            accumulated_data={"data": 1},
            sim_duration=100.0,
            scenario_name="scen_1",
            net_file_path="mock.net.xml",
            run_id=1,
            db_manager=mock_db,
        )
        assert sas_queue.put.called
        assert sas_queue.put.call_args[0][0]["status"] == "error"


def test_analyzer_engine_run_analysis_success_pipeline(base_analyzer, tmp_path):
    engine, _, db_queue, sas_queue, _ = base_analyzer

    mock_db = MagicMock()
    mock_db.get_fluid_dynamics_time_range.return_value = 3600.0
    mock_db.get_fluid_dynamics_min_max_timestamps.return_value = (
        datetime(2026, 1, 1, 12, 0, 0),
        datetime(2026, 1, 1, 13, 0, 0),
    )

    with patch("src.utils.paths.get_base_output_dir", return_value=str(tmp_path)), \
         patch("src.sas.analyzer_engine.AnalyzerDataProcessor") as MockProc, \
         patch("src.sas.report_generator.ReportGenerator") as MockRepGen, \
         patch("src.sas.heatmap_calibrator.HeatmapCalibrator") as MockCalib:

        # Mock Processor
        mock_proc_instance = MagicMock()
        mock_proc_instance.process_historical_data.return_value = ({"j1": {"flow": 100}}, ["j1"])
        MockProc.return_value = mock_proc_instance

        # Mock Analyzer
        engine.analyzer = MagicMock()
        engine.analyzer.analyze_collected_data.return_value = {
            "summary": "OK",
            "report_content": "Content",
            "new_cache_data": {"cache": 1},
            "analysis_results": {"j1": {"recommendation": "INSTALL_TLS", "warrant_details": {}}},
            "significant_change": True,
        }

        # Mock Cache Manager
        engine.cache_manager = MagicMock()
        engine.cache_manager.load_cache.return_value = ({}, True)

        # Mock Map Generator
        engine.map_generator = MagicMock()

        # Mock ReportGenerator
        mock_rep = MagicMock()
        mock_rep.generate_docx_report.return_value = ("report.docx", "Detailed Text")
        MockRepGen.return_value = mock_rep

        # Mock Calibrator
        mock_calib = MagicMock()
        mock_calib.is_available.return_value = True
        mock_calib.calibrate.return_value = {"weight": 1.0}
        MockCalib.return_value = mock_calib

        engine.run_analysis(
            accumulated_data={"data": 1},
            sim_duration=100.0,
            scenario_name="scen_full",
            net_file_path="mock.net.xml",
            run_id=10,
            calibration_data_points=[{"x": 1}],
            db_manager=mock_db,
        )

        assert engine.cache_manager.save_cache.called
        assert db_queue.put.called
        assert engine.map_generator.generate_map.called
        assert mock_rep.generate_docx_report.called
        assert sas_queue.put.called
        ui_res = sas_queue.put.call_args[0][0]
        assert ui_res["status"] == "success"
        assert "j1" in ui_res["analysis_results"]
        assert mock_calib.save_live_weights.called
