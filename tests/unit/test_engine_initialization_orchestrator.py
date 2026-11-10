# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Unit tests for src/engine/initialization_orchestrator.py
"""

import json
import os
import tempfile
from unittest.mock import MagicMock, patch
import pytest

from src.engine.initialization_orchestrator import InitializationOrchestrator


class TestInitializationOrchestrator:
    @pytest.fixture
    def mock_locale(self):
        lm = MagicMock()
        lm.get_string.side_effect = lambda k, default=None, **kw: default or k
        return lm

    @pytest.fixture
    def mock_settings(self):
        return {
            "ANALYSIS": {},
            "SUMO": {"scenario": "test_scenario.sumocfg"},
        }

    def test_write_system_summary_success_and_error(self, mock_locale, mock_settings):
        with tempfile.TemporaryDirectory() as tmp_dir:
            orch = InitializationOrchestrator(
                settings=mock_settings,
                log_dir=tmp_dir,
                gpu_info="NVIDIA RTX 4090",
                locale_manager=mock_locale,
            )

            # Success path
            orch._write_system_summary(
                scenario_results_dir=tmp_dir,
                agent_count={"local_agents": 2},
                network_topology={"nodes": 2, "edges": 1},
                agent_ids=["tl_2", "tl_1"],
            )

            status_file = os.path.join(tmp_dir, "status.json")
            assert os.path.exists(status_file)
            with open(status_file, "r") as f:
                data = json.load(f)
            assert data["gpu_info"] == "NVIDIA RTX 4090"
            assert data["agent_ids"] == ["tl_1", "tl_2"]

            # Error path (e.g. read-only dir or bad write)
            with patch("builtins.open", side_effect=OSError("Disk full")):
                orch._write_system_summary(tmp_dir, {}, {}, [])

    def test_initialize_system_scenario_path_error(self, mock_locale, mock_settings):
        orch = InitializationOrchestrator(
            settings=mock_settings,
            log_dir="/tmp",
            gpu_info="Mock CPU",
            locale_manager=mock_locale,
        )

        with patch("src.engine.initialization_orchestrator.SumoEnvironment") as mock_env_cls:
            mock_env = MagicMock()
            mock_env.scenario_path = "Desconhecido"
            mock_env_cls.return_value = mock_env

            with pytest.raises(RuntimeError):
                orch.initialize_system()

    def test_initialize_system_success(self, mock_locale, mock_settings):
        with tempfile.TemporaryDirectory() as tmp_dir:
            orch = InitializationOrchestrator(
                settings=mock_settings,
                log_dir=tmp_dir,
                gpu_info="Mock GPU",
                locale_manager=mock_locale,
            )

            with (
                patch("src.engine.initialization_orchestrator.SumoEnvironment") as mock_env_cls,
                patch("src.engine.initialization_orchestrator.AssetManager") as mock_asset_cls,
                patch("src.engine.initialization_orchestrator.build_structural_neighborhood_map") as mock_build_map,
                patch("src.engine.initialization_orchestrator.LifecycleManager"),
                patch("src.engine.initialization_orchestrator.ChildhoodAnalyzer"),
                patch("src.engine.initialization_orchestrator.MonitorClient") as mock_monitor_cls,
                patch("src.engine.initialization_orchestrator.SettingsManager"),
                patch("src.utils.paths.get_base_output_dir", return_value=tmp_dir),
            ):
                mock_env = MagicMock()
                mock_env.scenario_path = "/tmp/scenarios/grid4x4.sumocfg"
                mock_env.conn.simulation.getOption.return_value = "/tmp/net.xml"
                mock_env.get_traffic_light_ids.return_value = ["tl_1", "tl_2"]
                mock_env_cls.return_value = mock_env

                mock_asset = MagicMock()
                mock_asset.create_map_with_icons.return_value = (None, (["node1"], ["edge1"]))
                mock_asset_cls.return_value = mock_asset

                mock_build_map.return_value = {"tl_1": ["tl_2"], "tl_2": ["tl_1"]}
                mock_monitor = MagicMock()
                mock_monitor_cls.return_value = mock_monitor

                components = orch.initialize_system()

                assert components["env"] == mock_env
                assert mock_env.connect.called
                assert mock_asset.create_map_with_icons.called
                assert mock_asset.generate_coordinates_file.called
                assert mock_monitor.start.called
                assert "scenario_results_dir" in components
