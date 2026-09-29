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

# File: tests/unit/test_planning_export_handler.py
# Author: Gabriel Moraes
# Date: August 13, 2026

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
