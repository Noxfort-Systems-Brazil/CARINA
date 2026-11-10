# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Unit tests for src/manager/agent_population_loader.py
"""

import os
import tempfile
from unittest.mock import MagicMock, patch
import pytest

from src.core.enums import Maturity
from src.manager.agent_population_loader import AgentPopulationLoader


class TestAgentPopulationLoader:
    @pytest.fixture
    def mock_settings(self):
        s = MagicMock()
        s.getint.return_value = 40
        return s

    @pytest.fixture
    def mock_locale(self):
        lm = MagicMock()
        lm.get_string.side_effect = lambda k, default=None, **kw: default or k
        return lm

    def test_load_topology_fresh_and_existing_checkpoints(self, mock_settings, mock_locale):
        with tempfile.TemporaryDirectory() as tmp_dir:
            loader = AgentPopulationLoader(
                settings=mock_settings,
                locale_manager=mock_locale,
                log_dir=tmp_dir,
            )

            state_extractor = MagicMock()
            state_extractor.get_observation_space_size.return_value = 32
            maturity_manager = MagicMock()

            # Mock sumolib net
            tls_1 = MagicMock()
            tls_1.getID.return_value = "tl_1"
            tls_2 = MagicMock()
            tls_2.getID.return_value = "tl_2"

            mock_net = MagicMock()
            mock_net.getTrafficLights.return_value = [tls_1, tls_2]
            mock_net.getEdges.return_value = ["e1", "e2"]

            # Mock checkpoint existence: tl_1 exists, tl_2 fresh
            ckpt_dir = os.path.join(tmp_dir, "results", "hft_live_session", "checkpoints")
            os.makedirs(ckpt_dir, exist_ok=True)
            tl1_ckpt = os.path.join(ckpt_dir, "agent_tl_1.pth")
            open(tl1_ckpt, "w").close()

            with (
                patch("sumolib.net.readNet", return_value=mock_net),
                patch("src.manager.agent_population_loader.get_base_output_dir", return_value=tmp_dir),
                patch("src.manager.agent_population_loader.LocalAgent") as mock_agent_cls,
                patch("src.promotion.maturity_pacing_calculator.MaturityPacingCalculator.apply_if_enabled"),
                patch("src.promotion.performance_margin_calculator.PerformanceMarginCalculator.calculate_from_topology", return_value=0.1),
                patch("src.promotion.performance_margin_calculator.PerformanceMarginCalculator.apply_if_enabled"),
                patch("src.engine.reward_weights_calculator.RewardWeightsCalculator.calculate_from_topology", return_value={}),
                patch("src.engine.reward_weights_calculator.RewardWeightsCalculator.apply_if_enabled"),
            ):
                agent_instance = MagicMock()
                agent_instance.load_checkpoint.return_value = "TEEN"
                mock_agent_cls.return_value = agent_instance

                agents, initial_phases = loader.load_topology(
                    map_path="/tmp/map.net.xml",
                    state_extractor=state_extractor,
                    maturity_manager=maturity_manager,
                    shared_pae=None,
                )

                assert len(agents) == 2
                assert "tl_1" in agents and "tl_2" in agents
                assert initial_phases == {"tl_1": 0, "tl_2": 0}
                assert state_extractor.load_topology.called
                # Check maturity restoration for tl_1
                maturity_manager.set_agent_phase.assert_any_call("tl_1", Maturity.TEEN)
                # Check initial checkpoint creation for tl_2
                assert agent_instance.save_checkpoint.called

    def test_load_topology_critical_error_raises(self, mock_settings, mock_locale):
        loader = AgentPopulationLoader(
            settings=mock_settings,
            locale_manager=mock_locale,
            log_dir="/tmp",
        )
        state_extractor = MagicMock()
        maturity_manager = MagicMock()

        with patch("sumolib.net.readNet", side_effect=OSError("File corrupted")):
            with pytest.raises(OSError):
                loader.load_topology(
                    map_path="/bad/map.net.xml",
                    state_extractor=state_extractor,
                    maturity_manager=maturity_manager,
                )
