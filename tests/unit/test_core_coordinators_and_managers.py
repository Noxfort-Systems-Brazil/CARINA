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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# File: tests/unit/test_core_coordinators_and_managers.py
# Author: Gabriel Moraes
# Date: September 2026

import os
from collections import Counter
from unittest.mock import MagicMock, patch

import pytest

import core.traci_proxy as traci_proxy
from core.enums import Maturity
from core.inference_engine import InferenceEngine
from core.lifecycle_manager import LifecycleManager
from core.maturity_reporter import MaturityReporter
from core.observation_builder import ObservationBuilder
from core.population_manager import PopulationManager
from core.strategic_coordinator import StrategicCoordinator
from core.system_reporter import SystemReporter


@pytest.fixture
def mock_locale():
    lm = MagicMock()
    lm.get_string.side_effect = lambda key, fallback=None, **kwargs: fallback or key
    return lm


def test_system_reporter_step_start(mock_locale):
    """SystemReporter must format step header and operating mode."""
    with patch("logging.info") as mock_log:
        SystemReporter.report_step_start(mock_locale, step=1, sim_time=10.0, operation_mode="AUTO")
        assert mock_log.called


def test_system_reporter_agent_creation(mock_locale):
    """SystemReporter must log agent creation and AMP status."""
    with patch("logging.info") as mock_log:
        SystemReporter.report_agent_creation("TL_10", True, mock_locale)
        assert mock_log.called


def test_system_reporter_school_bulletin(mock_locale):
    """SystemReporter must tally and log maturity counts."""
    maturity_counts = Counter({Maturity.CHILD: 2, Maturity.TEEN: 1, Maturity.ADULT: 3})
    with patch("logging.info") as mock_log:
        SystemReporter.report_school_bulletin(
            mock_locale,
            episode_count=5,
            total_reward=250.0,
            maturity_counts=maturity_counts,
            calibration_status="Concluída",
        )
        assert mock_log.called


def test_system_reporter_graph_structure(mock_locale):
    """SystemReporter must log graph node and edge counts."""
    with patch("logging.info") as mock_log:
        SystemReporter.report_graph_structure(num_nodes=10, num_edges=20, lm=mock_locale)
        assert mock_log.called


def test_system_reporter_agent_decision(mock_locale):
    """SystemReporter must log agent decision and override status."""
    with patch("logging.info") as mock_log:
        SystemReporter.report_agent_decision(
            lm=mock_locale,
            tl_id="TL_1",
            maturity_level="ADULT",
            action_str="Phase 0",
            is_authorized=True,
            reason="Safe",
            override_state="NORMAL",
        )
        assert mock_log.called


def test_traci_proxy_pipeline():
    """TraciProxy forwards requests over multiprocessing Pipe connection."""
    mock_pipe = MagicMock()
    mock_pipe.recv.return_value = ["TL_1", "TL_2"]

    traci_proxy.init_proxy_pipe(mock_pipe)

    # Top-level intercepted calls
    traci_proxy.connect()
    traci_proxy.close()
    traci_proxy.setOrder(1)

    # Module call
    tl_list = traci_proxy.trafficlight.getIDList()
    assert tl_list == ["TL_1", "TL_2"]
    assert mock_pipe.send.called


def test_traci_proxy_not_initialized():
    """TraciProxy raises RuntimeError if pipe is None."""
    traci_proxy._PIPE_CONN = None
    with pytest.raises(RuntimeError):
        traci_proxy.trafficlight.getIDList()


def test_inference_engine_execution():
    """InferenceEngine calls agent model forward pass."""
    engine = InferenceEngine()
    mock_agent = MagicMock()
    mock_agent.device.type = "cpu"
    mock_action_tensor = MagicMock()
    mock_action_tensor.item.return_value = 1
    mock_agent.choose_action.return_value = (mock_action_tensor, 0.1, 0.5, 0.2)

    action, action_t, log_prob, state_val, entropy = engine.predict(mock_agent, state_sequence=[[0.1, 0.2, 0.3]])
    assert action == 1
    assert entropy == 0.2
    assert mock_agent.choose_action.called


def test_observation_builder_gather_messages():
    """ObservationBuilder formats message vectors across traffic lights."""
    builder = ObservationBuilder(message_size=4, n_observations=10)
    current_states = {
        "TL_1": [0.5, 0.2, 0.1, 0.0],
        "TL_2": [0.1, 0.8, 0.3, 0.4],
    }
    mock_green_phases_fn = MagicMock(return_value=[0, 1])

    messages = builder.gather_messages(current_states, mock_green_phases_fn)
    assert "TL_1" in messages
    assert "TL_2" in messages


def test_lifecycle_manager_initialization(mock_locale, tmp_path):
    """LifecycleManager loads maturity promotion parameters from settings."""
    mock_settings = MagicMock()
    log_dir = str(tmp_path / "logs")
    results_dir = str(tmp_path / "results")

    lm_mgr = LifecycleManager(mock_settings, log_dir, results_dir, mock_locale)
    assert lm_mgr.locale_manager == mock_locale
    assert os.path.exists(lm_mgr.scenario_checkpoint_dir)


def test_population_manager_pbt_loading(mock_locale):
    """PopulationManager loads PBT configuration correctly."""
    mock_settings = MagicMock()
    mock_settings.has_section.return_value = True
    pbt_section = MagicMock()
    pbt_section.getint.side_effect = lambda k, fallback=None: 20 if "freq" in k else 30
    pbt_section.get.side_effect = lambda k: "0.0001, 0.001"
    mock_settings.__getitem__.return_value = pbt_section

    mock_lc = MagicMock()
    pop_mgr = PopulationManager(mock_settings, mock_lc, mock_locale)
    assert pop_mgr.pbt_config["evolution_freq"] == 20
    assert pop_mgr.pbt_config["exploit_percentile"] == 30


def test_strategic_coordinator_init():
    """StrategicCoordinator initializes GAT settings and consultant agent."""
    mock_locale = MagicMock()
    mock_settings = MagicMock()
    gat_mock = MagicMock()
    gat_mock.getint.side_effect = lambda k: 60 if k == "update_frequency_seconds" else 16
    mock_settings.__getitem__.side_effect = lambda k: gat_mock if k == "GAT_STRATEGIST" else MagicMock()

    coord = StrategicCoordinator(settings=mock_settings, device="cpu", locale_manager=mock_locale)
    assert coord.update_frequency == 60
    assert coord.output_dim == 16


def test_maturity_reporter_promotion(mock_locale):
    """MaturityReporter reports agent graduation and promotion."""
    reporter = MaturityReporter(locale_manager=mock_locale)
    with patch("logging.info") as mock_log:
        reporter.report_promotion("TL_1", Maturity.ADULT, {"accuracy": "95%", "episodes": 100})
        assert mock_log.called
    with patch("logging.info") as mock_log:
        reporter.report_promotion("TL_1", Maturity.TEEN, {"episodes": 50})
        assert mock_log.called


def test_maturity_reporter_rejection(mock_locale):
    """MaturityReporter reports reasons when criteria are not met."""
    reporter = MaturityReporter(locale_manager=mock_locale)
    details = {
        "reward_threshold": {"ok": False, "msg": "Reward -120 below -50 required"},
        "entropy_stability": {"ok": True, "msg": "Entropy 0.05 stable"},
    }
    with patch("logging.info") as mock_log:
        reporter.report_rejection("TL_2", Maturity.CHILD, Maturity.TEEN, details)
        assert mock_log.called
