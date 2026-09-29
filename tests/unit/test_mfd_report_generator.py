# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: tests/unit/test_mfd_report_generator.py
# Author: Gabriel Moraes
# Date: September 2026

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from mfd.mfd_report_generator import MFDReportGenerator


def test_mfd_report_generator_empty_history():
    result = MFDReportGenerator.generate_report({"history": []})
    assert result["status"] == "error"
    assert "insuficientes ou incompletos" in result["message"] or "No MFD history" in result["message"]


@pytest.fixture(autouse=True)
def mock_default_settings():
    with patch("utils.settings_manager.SettingsManager.load_settings", return_value={"xai_speed_unit": "m/s"}):
        yield


@patch("slm.local_llama_transducer.LocalLlamaTransducer.generate_report", return_value="")
@patch("subprocess.run")
def test_mfd_report_generator_first_analysis(mock_run, mock_llama, tmp_path):
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = "Executivo: O trânsito melhorou. Análise das 12:00..."
    mock_run.return_value = mock_proc

    history = [
        {
            "accumulation": 5.0,
            "production": 10.0,
            "mean_speed": 12.0,
            "efficiency": 0.8,
            "congestion_ratio": 0.1,
            "intersections": {
                "intersection_1": {"accumulation": 2.0, "production": 4.0, "mean_speed": 10.0, "queue_length": 1.5}
            },
        },
        {
            "accumulation": 6.0,
            "production": 12.0,
            "mean_speed": 13.0,
            "efficiency": 0.85,
            "congestion_ratio": 0.15,
            "intersections": {
                "intersection_1": {"accumulation": 3.0, "production": 5.0, "mean_speed": 11.0, "queue_length": 1.0}
            },
        },
    ]

    mfd_data = {"history": history, "peak_production": 15.0, "peak_accumulation": 7.0}

    result = MFDReportGenerator.generate_report(mfd_data, scenario_results_dir=str(tmp_path))
    assert result["status"] == "complete"
    assert "image_base64" in result
    assert "text_report" in result
    assert "Executivo: O trânsito melhorou. Análise das 12:00..." in result["text_report"]

    last_analysis_file = os.path.join(tmp_path, "mfd_last_analysis.json")
    first_analysis_file = os.path.join(tmp_path, "mfd_first_analysis.json")
    assert os.path.exists(last_analysis_file)
    assert os.path.exists(first_analysis_file)

    with open(last_analysis_file, "r") as f:
        saved_data = json.load(f)
    assert "timestamp" in saved_data
    assert "global_stats" in saved_data
    assert "intersections_stats" in saved_data
    assert saved_data["intersections_stats"]["intersection_1"]["average_speed_m_s"] == 10.5

    with open(first_analysis_file, "r") as f:
        first_saved = json.load(f)
    assert first_saved["intersections_stats"]["intersection_1"]["average_speed_m_s"] == 10.5

    assert mock_run.called
    called_args, called_kwargs = mock_run.call_args_list[0]
    transducer_input = json.loads(called_kwargs["input"])

    attrs = transducer_input["attributions"]
    assert "comparison_since_last_analysis" in attrs
    assert "comparison_since_first_analysis" in attrs
    assert "intersections_current" in attrs
    assert "first_analysis_timestamp" in transducer_input

    assert attrs["comparison_since_last_analysis"]["global_outcome"] == "FIRST_ANALYSIS"
    assert attrs["comparison_since_first_analysis"]["global_outcome"] == "FIRST_ANALYSIS"


@patch("slm.local_llama_transducer.LocalLlamaTransducer.generate_report", return_value="")
@patch("subprocess.run")
@patch("utils.settings_manager.SettingsManager.load_settings")
def test_mfd_report_generator_speed_units_and_integers(mock_load_settings, mock_run, mock_llama, tmp_path):
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = "Report with custom speed unit."
    mock_run.return_value = mock_proc

    mock_load_settings.return_value = {"xai_speed_unit": "km/h"}

    history = [
        {
            "accumulation": 5.4,
            "production": 10.0,
            "mean_speed": 10.0,
            "efficiency": 0.8,
            "congestion_ratio": 0.1,
            "intersections": {
                "intersection_1": {"accumulation": 2.6, "production": 4.0, "mean_speed": 10.0, "queue_length": 1.7}
            },
        }
    ]

    mfd_data = {"history": history, "peak_production": 15.0, "peak_accumulation": 7.3}

    result = MFDReportGenerator.generate_report(mfd_data, scenario_results_dir=str(tmp_path))
    assert result["status"] == "complete"

    assert mock_run.called
    called_args, called_kwargs = mock_run.call_args_list[0]
    transducer_input = json.loads(called_kwargs["input"])
    attrs = transducer_input["attributions"]

    assert attrs["speed_unit"] == "km/h"
    assert attrs["average_speed"] == 36.0
    assert attrs["average_accumulation_veh"] == 5
    assert attrs["critical_accumulation_veh"] == 7

    inter_current = attrs["intersections_current"]["intersection_1"]
    assert inter_current["average_queue_length"] == 2
    assert inter_current["average_accumulation"] == 3
