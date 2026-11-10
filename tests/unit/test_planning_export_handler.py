# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
from unittest.mock import MagicMock, patch

import pytest

from ui.handlers.planning_export_handler import PlanningExportHandler


def test_load_scenario_map_base64_none():
    res = PlanningExportHandler.load_scenario_map_base64(None)
    assert res == ""


@patch("os.path.exists")
@patch("builtins.open", new_callable=pytest.importorskip("unittest.mock").mock_open, read_data=b"fake_image_bytes")
def test_load_scenario_map_base64_success(mock_file, mock_exists):
    mock_exists.return_value = True
    res = PlanningExportHandler.load_scenario_map_base64("/fake/dir")
    assert isinstance(res, str)
    assert len(res) > 0


@patch("ui.handlers.planning_export_handler.ReportExporter.export_report")
def test_export_report_success(mock_export):
    mock_export.return_value = True
    mock_lm = MagicMock()
    mock_lm.get_string.return_value = "Relatório salvo."

    success, msg = PlanningExportHandler.export_report(
        page=MagicMock(), locale_manager=mock_lm, save_path="/fake/path/report.docx", report_content="Report body text"
    )

    assert success is True
    assert msg == "Relatório salvo."
    mock_export.assert_called_once()
