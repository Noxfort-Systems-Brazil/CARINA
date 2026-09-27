# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
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

# File: tests/unit/test_xai_attribution_and_repository.py
# Author: Gabriel Moraes
# Date: September 2026

# CARINA - Clean Architecture & SOLID Unit Test Suite
# Tests for NetworkAttributionAggregator and XaiAgentRepository

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from xai.network_attribution_aggregator import NetworkAttributionAggregator
from xai.xai_agent_repository import XaiAgentRepository


@pytest.fixture
def mock_locale():
    lm = MagicMock()
    lm.get_string.side_effect = lambda key, **kwargs: f"[{key}]"
    return lm


def test_network_attribution_aggregator_empty(mock_locale):
    """Tests that empty input returns blank base64 chart and empty list."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        aggregator = NetworkAttributionAggregator(tmp_dir, mock_locale)
        res = aggregator.aggregate_network_analysis({})
        assert res["global_image_base64"] == ""
        assert res["aggregated_analysis"] == []


def test_network_attribution_aggregator_multi_agent(mock_locale):
    """Tests aggregating attribution from multiple agents and generating chart."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        aggregator = NetworkAttributionAggregator(tmp_dir, mock_locale)

        mock_analyses = {
            "Agent_1": {
                "sorted_analysis": [
                    {"name": "Fila Norte", "importance": 0.8, "description": "Fila na via N"},
                    {"name": "Velocidade Média", "importance": 0.2, "description": "Velocidade"},
                ]
            },
            "Agent_2": {
                "sorted_analysis": [
                    {"name": "Fila Norte", "importance": 0.6, "description": "Fila na via N"},
                    {"name": "Velocidade Média", "importance": 0.4, "description": "Velocidade"},
                ]
            },
        }

        with patch("xai.network_attribution_aggregator.ChartRenderer") as mock_renderer_cls:
            mock_renderer = MagicMock()
            mock_renderer.render_to_bytes.return_value = b"fake_png_bytes"
            mock_renderer_cls.return_value = mock_renderer

            result = aggregator.aggregate_network_analysis(mock_analyses)

            assert len(result["aggregated_analysis"]) == 2
            # Average for "Fila Norte": (0.8 + 0.6) / 2 = 0.7
            fila_norte = next(item for item in result["aggregated_analysis"] if item["name"] == "Fila Norte")
            assert pytest.approx(fila_norte["importance"]) == 0.7

            assert result["global_image_base64"] != ""
            assert os.path.exists(os.path.join(tmp_dir, "xai_importance.png"))


def test_xai_agent_repository_discovery(mock_locale):
    """Tests discovering agents from checkpoint files and database records."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        checkpoints_dir = os.path.join(tmp_dir, "checkpoints")
        os.makedirs(checkpoints_dir, exist_ok=True)

        # Create checkpoint files
        with open(os.path.join(checkpoints_dir, "agent_C1.pth"), "w") as f:
            f.write("model")
        with open(os.path.join(checkpoints_dir, "agent_C2.pth"), "w") as f:
            f.write("model")

        repo = XaiAgentRepository(tmp_dir, mock_locale)

        # Mock database manager returning agent C3
        with patch("database.database_manager.DatabaseManager") as mock_db_cls:
            mock_db = MagicMock()
            mock_db.step_decision_repo.get_all_audited_agent_ids.return_value = ["C3", "ALL"]
            mock_db_cls.return_value = mock_db

            agents = repo.discover_audited_agent_ids(primary_agent_id="C4")

            # Check that ALL was filtered out and C1, C2, C3, C4 were discovered
            assert "ALL" not in agents
            assert "C1" in agents
            assert "C2" in agents
            assert "C3" in agents
            assert "C4" in agents
            assert sorted(agents) == ["C1", "C2", "C3", "C4"]
