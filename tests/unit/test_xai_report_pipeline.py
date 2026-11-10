# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import os
from unittest.mock import MagicMock, patch
import pytest

from src.xai.report_pipeline import ReportPipeline


@pytest.fixture
def pipeline_fixture(tmp_path):
    scen_dir = str(tmp_path / "scen")
    reports_dir = str(tmp_path / "reports")
    os.makedirs(scen_dir, exist_ok=True)
    os.makedirs(reports_dir, exist_ok=True)
    return ReportPipeline(scen_dir, reports_dir)


def test_report_pipeline_init(pipeline_fixture):
    assert pipeline_fixture.scenario_results_dir is not None
    assert pipeline_fixture.reports_dir is not None
    assert "semantic_transducer.py" in pipeline_fixture.transducer_script


def test_report_pipeline_fallback_sorted_analysis(pipeline_fixture):
    fallback = pipeline_fixture._get_fallback_sorted_analysis()
    assert len(fallback) == 4
    assert fallback[0]["importance"] == 0.485
    assert "name" in fallback[0]


def test_report_pipeline_parse_captum_text_report_content(pipeline_fixture):
    sample_text = """
    ● Sensor: queue_length
      Impact: High (0.485)
    ● Sensor / Variável: occupancy_rate
      Impact: Medium (-0.312)
    ● Sensor: invalid_number
      Impact: None (not_a_float)
    """
    res = pipeline_fixture._parse_captum_text_report_content(sample_text)
    assert res.get("queue_length") == 0.485
    assert res.get("occupancy_rate") == -0.312
    assert "invalid_number" not in res


def test_report_pipeline_parse_captum_text_report_file(pipeline_fixture, tmp_path):
    report_file = tmp_path / "report.txt"
    report_file.write_text("● Sensor: queue_length\n (0.485)", encoding="utf-8")

    res = pipeline_fixture._parse_captum_text_report(str(report_file))
    assert res.get("queue_length") == 0.485

    # File not found error handled
    empty_res = pipeline_fixture._parse_captum_text_report("non_existent.txt")
    assert empty_res == {}


def test_report_pipeline_generate_full_report_success_transducer(pipeline_fixture):
    mock_agent = MagicMock()

    with patch("src.xai.report_pipeline.CaptumAnalyzer") as MockCaptum, \
         patch("src.xai.report_pipeline.SettingsManager") as MockSettings, \
         patch("subprocess.run") as mock_subproc:

        mock_captum_inst = MagicMock()
        mock_captum_inst.generate_analysis_in_memory.return_value = {
            "image_base64": "img_data",
            "text_report": "raw text report",
            "sorted_analysis": [{"name": "queue", "importance": 0.5}],
        }
        MockCaptum.return_value = mock_captum_inst

        mock_settings_inst = MagicMock()
        mock_settings_inst.load_settings.return_value = {
            "xai_slm_device": "cpu",
            "xai_slm_gpu_layers": "0",
            "xai_speed_unit": "imperial",
        }
        MockSettings.return_value = mock_settings_inst

        # Subprocess returns success
        mock_subproc.return_value = MagicMock(returncode=0, stdout="Transduced Narrative Report", stderr="")

        res = pipeline_fixture.generate_full_report(mock_agent, "TL_1")

        assert res["status"] == "complete"
        assert res["image_base64"] == "img_data"
        assert res["text_content"] == "Transduced Narrative Report"


def test_report_pipeline_generate_full_report_empty_captum_and_subproc_fail(pipeline_fixture):
    mock_agent = MagicMock()

    with patch("src.xai.report_pipeline.CaptumAnalyzer") as MockCaptum, \
         patch("subprocess.run") as mock_subproc:

        mock_captum_inst = MagicMock()
        mock_captum_inst.generate_analysis_in_memory.return_value = None  # Empty Captum result
        MockCaptum.return_value = mock_captum_inst

        # Subprocess fails
        mock_subproc.return_value = MagicMock(returncode=1, stdout="", stderr="Crash")

        res = pipeline_fixture.generate_full_report(mock_agent, "TL_1")

        assert res["status"] == "complete"
        # Falls back to default text report
        assert isinstance(res["text_content"], str)


def test_report_pipeline_generate_full_report_subproc_exception(pipeline_fixture):
    mock_agent = MagicMock()

    with patch("src.xai.report_pipeline.CaptumAnalyzer") as MockCaptum, \
         patch("subprocess.run", side_effect=OSError("Exec error")):

        mock_captum_inst = MagicMock()
        mock_captum_inst.generate_analysis_in_memory.return_value = {
            "image_base64": "img",
            "text_report": "fallback text",
            "sorted_analysis": [{"name": "queue", "importance": 0.5}],
        }
        MockCaptum.return_value = mock_captum_inst

        res = pipeline_fixture.generate_full_report(mock_agent, "TL_1")

        assert res["status"] == "complete"
        assert res["text_content"] == "fallback text"
