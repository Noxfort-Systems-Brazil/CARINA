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

# File: tests/unit/test_engine_runners_and_coordinators.py
# Author: Gabriel Moraes
# Date: September 2026

import queue
from unittest.mock import MagicMock, patch

import pytest

from core.enums import Maturity
from engine.analysis_runner import AnalysisRunner
from engine.post_episode_coordinator import PostEpisodeCoordinator


@pytest.fixture
def mock_locale():
    lm = MagicMock()
    lm.get_string.side_effect = lambda key, fallback=None, **kwargs: fallback or key
    return lm


def test_analysis_runner_execution(mock_locale):
    """AnalysisRunner executes analysis episodes, computes baseline, and saves to cache."""
    mock_runner = MagicMock()
    mock_runner.run.return_value = {"TL_1": {"reward": 100.0, "entropy": 0.5}}

    mock_analyzer = MagicMock()
    mock_analyzer.analysis_episodes = 2
    mock_analyzer.locale_manager = mock_locale
    mock_analyzer.run_analysis.return_value = ({"profiles": {}}, {"mean_reward": 100.0})

    runner = AnalysisRunner(mock_runner, mock_analyzer)
    profiles, baseline = runner.run()

    assert mock_runner.run.call_count == 2
    assert mock_analyzer.run_analysis.called
    assert mock_analyzer.save_to_cache.called
    assert baseline["mean_reward"] == 100.0


def test_post_episode_coordinator_run(mock_locale, tmp_path):
    """PostEpisodeCoordinator handles promotions, PBT evolution, and checkpointing."""
    mock_settings = MagicMock()
    mock_settings.getint.side_effect = lambda sec, key, fallback=None: 1 if "save" in key else 1
    pbt_dict = MagicMock()
    pbt_dict.getint.return_value = 1
    mock_settings.__getitem__.return_value = pbt_dict

    mock_pop_mgr = MagicMock()
    mock_agent = MagicMock()
    mock_pop_mgr.agents = {"TL_1": mock_agent}

    mock_maturity_mgr = MagicMock()
    mock_maturity_mgr.check_and_promote_agents.return_value = True
    mock_maturity_mgr.agent_maturity = {"TL_1": Maturity.TEEN}
    mock_maturity_mgr.get_state.return_value = {"TL_1": "TEEN"}

    mock_lifecycle_mgr = MagicMock()
    mock_lifecycle_mgr.scenario_checkpoint_dir = str(tmp_path)

    db_queue = queue.Queue()

    coordinator = PostEpisodeCoordinator(
        settings=mock_settings,
        population_manager=mock_pop_mgr,
        maturity_manager=mock_maturity_mgr,
        lifecycle_manager=mock_lifecycle_mgr,
        db_data_queue=db_queue,
        run_id=42,
        locale_manager=mock_locale,
    )

    episode_metrics = {"TL_1": {"reward": 80.0, "entropy": 0.05}}

    with (
        patch("traci.update_maturity_state", create=True) as mock_traci_update,
        patch("core.system_reporter.SystemReporter.report_school_bulletin") as mock_bulletin,
    ):
        coordinator.run(episode_count=1, episode_metrics=episode_metrics)

        assert mock_traci_update.called
        assert mock_pop_mgr.collect_episode_rewards.called
        assert mock_pop_mgr.evolve.called
        assert mock_maturity_mgr.save_state.called
        assert mock_lifecycle_mgr.save_all_checkpoints.called
        assert mock_bulletin.called
        assert not db_queue.empty()
        packet = db_queue.get_nowait()
        assert packet["payload"]["run_id"] == 42
        assert packet["payload"]["total_reward"] == 80.0
