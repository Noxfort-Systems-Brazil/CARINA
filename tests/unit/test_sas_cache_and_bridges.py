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

# File: tests/unit/test_sas_cache_and_bridges.py
# Author: Gabriel Moraes
# Date: September 2026

# CARINA - Clean Architecture & SOLID Unit Test Suite
# Tests for SAS Analysis Cache Manager, TopologyRecorderBridge, and PlanningMapGenerator

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from sas.sas_analysis_cache_manager import SASAnalysisCacheManager
from sas.sas_planning_map_generator import SASPlanningMapGenerator
from sas.topology_recorder_bridge import TopologyRecorderBridge


@pytest.fixture
def mock_locale():
    lm = MagicMock()
    lm.get_string.side_effect = lambda key, **kwargs: f"[{key}]"
    return lm


def test_sas_analysis_cache_manager_db_and_file_fallback():
    """Tests loading and saving SAS analysis cache from DB and filesystem fallback."""
    cache_mgr = SASAnalysisCacheManager()

    with tempfile.TemporaryDirectory() as tmp_dir:
        # 1. Fallback when DB has no cache but file exists
        file_cache = {"J1": {"warrant_met": True}}
        cache_path = os.path.join(tmp_dir, "sas_last_analysis.json")
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(file_cache, f)

        mock_db = MagicMock()
        mock_db.get_sas_analysis_cache.return_value = None

        loaded, has_prev = cache_mgr.load_cache(mock_db, "scenario_1", tmp_dir)
        assert has_prev is True
        assert loaded == file_cache

        # 2. Saving cache updates both DB and JSON file
        new_data = {"J1": {"warrant_met": False, "score": 90}}
        cache_mgr.save_cache(mock_db, "scenario_1", tmp_dir, new_data)

        mock_db.save_sas_analysis_cache.assert_called_once_with("scenario_1", new_data)
        with open(cache_path, "r", encoding="utf-8") as f:
            saved_disk = json.load(f)
        assert saved_disk == new_data


def test_topology_recorder_bridge(mock_locale):
    """Tests topology extraction and propagation to TrafficDataRecorder."""
    mock_recorder = MagicMock()
    bridge = TopologyRecorderBridge(mock_recorder, mock_locale)

    with patch("utils.network_topology_parser.NetworkTopologyParser") as mock_parser_cls:
        mock_parser = MagicMock()
        mock_parser.build.return_value = (
            {"J1": "traffic_light"},
            {"J1": {"edge_A": {"length": 150.0, "num_lanes": 2, "speed_limit": 16.67}}},
        )
        mock_parser_cls.return_value = mock_parser

        bridge.update_recorder_topology("/fake/net.xml")

        assert mock_recorder.set_topology.called
        topo = mock_recorder.set_topology.call_args[0][0]
        assert "edge_A" in topo
        assert topo["edge_A"]["length"] == 150.0
        assert topo["edge_A"]["lanes"] == 2
        assert topo["edge_A"]["max_speed"] == 16.67


def test_sas_planning_map_generator(mock_locale):
    """Tests recommendation icon categorization and map rendering dispatch."""
    generator = SASPlanningMapGenerator(mock_locale)
    generator.map_renderer = MagicMock()

    analysis_results = {
        "J1": {"recommendation": "Adicionar semáforo no cruzamento"},
        "J2": {"recommendation": "Remover semáforo existente"},
        "J3": {"recommendation": "Cruzamento não sinalizado"},
        "J4": {"recommendation": "Manter operação atual"},
    }

    with tempfile.TemporaryDirectory() as tmp_dir:
        generator.generate_map(analysis_results, "/fake/net.xml", tmp_dir)

        assert generator.map_renderer.create_map_with_icons.called
        _, kwargs = generator.map_renderer.create_map_with_icons.call_args
        icons = kwargs.get("icon_requests") or generator.map_renderer.create_map_with_icons.call_args[0][1]

        assert icons["J1"] == "add"
        assert icons["J2"] == "remove"
        assert icons["J3"] == "no_signal"
        assert icons["J4"] == "existing"
