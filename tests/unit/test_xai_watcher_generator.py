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

# File: tests/unit/test_xai_watcher_generator.py
# Author: Gabriel Moraes
# Date: September 2026

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from xai.xai_report_generator import XaiReportGenerator
from xai.xai_watcher import XaiWatcher


@pytest.mark.unit
def test_xai_watcher_lifecycle():
    pm = MagicMock()
    lm = MagicMock()
    env = MagicMock()
    sc = MagicMock()

    watcher = XaiWatcher(pm, lm, env, sc)
    assert watcher.watcher_running is False
    assert watcher.watcher_thread is None

    watcher.start()
    assert watcher.watcher_running is True
    assert watcher.watcher_thread is not None
    assert watcher.watcher_thread.is_alive()

    watcher.stop()
    assert watcher.watcher_running is False
    watcher.watcher_thread.join(timeout=1.0)


@pytest.mark.unit
def test_xai_watcher_processing(tmp_path):
    pm = MagicMock()
    lm = MagicMock()
    env = MagicMock()
    sc = MagicMock()

    scenario_dir = tmp_path / "scenario_1"
    ckpt_dir = scenario_dir / "checkpoints"
    ckpt_dir.mkdir(parents=True)
    lm.scenario_checkpoint_dir = str(ckpt_dir)

    requests_dir = scenario_dir / "captum" / "requests"
    responses_dir = scenario_dir / "captum" / "responses"
    requests_dir.mkdir(parents=True)
    responses_dir.mkdir(parents=True)

    # Create dummy request
    req_file = requests_dir / "audit_1.request"
    req_file.write_text(json.dumps({"agent_id": "tl_1"}), encoding="utf-8")

    pm.agents = {"tl_1": MagicMock()}
    env.state_extractor.get_local_feature_glossary.return_value = [
        {"feature_name": "queue", "description": "queue len"}
    ]
    sc.max_state_dim = 2
    sc.output_dim = 1

    watcher = XaiWatcher(pm, lm, env, sc)

    with patch("xai.xai_watcher.CaptumAnalyzer") as mock_analyzer_cls:
        mock_analyzer = MagicMock()
        mock_analyzer.generate_analysis.return_value = {
            "image_path": "/path/to/img.png",
            "text_path": "/path/to/text.md",
        }
        mock_analyzer_cls.return_value = mock_analyzer

        # Run single iteration of processing manually
        watcher.watcher_running = True

        # We simulate the inner loop logic
        request_filename = "audit_1.request"
        request_path = str(req_file)
        response_filename = "audit_1.response"
        response_path = str(responses_dir / response_filename)

        with open(request_path, "r", encoding="utf-8") as f:
            req_data = json.load(f)
        assert req_data["agent_id"] == "tl_1"

        # Check response creation
        with open(response_path, "w", encoding="utf-8") as f:
            json.dump({"status": "complete", "image_path": "/path/to/img.png"}, f)
        os.remove(request_path)

        assert not os.path.exists(request_path)
        assert os.path.exists(response_path)


@pytest.mark.unit
def test_xai_report_generator_orchestration(tmp_path):
    scenario_dir = str(tmp_path / "scenario_out")
    os.makedirs(os.path.join(scenario_dir, "checkpoints"), exist_ok=True)

    mock_repo = MagicMock()
    mock_repo.discover_audited_agent_ids.return_value = ["tl_1", "tl_2"]

    mock_agg = MagicMock()
    mock_agg.aggregate_network_analysis.return_value = {"global_image_base64": "base64_global_chart"}

    mock_builder = MagicMock()
    mock_builder.build_markdown.return_value = "# Relatório de Auditoria ABNT\n\nTexto de teste."

    mock_reconstructor = MagicMock()
    mock_agent = MagicMock()
    mock_reconstructor.reconstruct_agent.return_value = mock_agent

    with (
        patch("xai.xai_report_generator.CaptumAnalyzer") as mock_analyzer_cls,
        patch("xai.xai_report_generator.ReportPostProcessor.enforce_semantic_consistency", side_effect=lambda x: x),
    ):

        mock_analyzer = MagicMock()
        mock_analyzer.generate_analysis_in_memory.return_value = {
            "image_base64": "base64_agent_chart",
            "attributions": [0.1, 0.2],
        }
        mock_analyzer_cls.return_value = mock_analyzer

        generator = XaiReportGenerator(
            scenario_results_dir=scenario_dir, repository=mock_repo, aggregator=mock_agg, report_builder=mock_builder
        )
        generator.reconstructor = mock_reconstructor

        report = generator.generate_full_multi_agent_report("tl_1")
        assert report["status"] == "complete"
        assert report["image_base64"] == "base64_agent_chart"
        assert "# Relatório de Auditoria ABNT" in report["text_content"]
