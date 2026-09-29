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

# File: tests/unit/test_engine_coordinators_and_reporters.py
# Author: Gabriel Moraes
# Date: September 2026

import queue
from unittest.mock import MagicMock, patch

import pytest

from core.enums import Maturity
from engine.asset_manager import AssetManager
from engine.episode_reporter import EpisodeReporter
from engine.guardian_communicator import GuardianCommunicator
from engine.service_manager import ServiceManager
from engine.state_history_manager import StateHistoryManager


@pytest.fixture
def mock_locale():
    lm = MagicMock()
    lm.get_string.side_effect = lambda key, fallback=None, **kwargs: fallback or key
    return lm


def test_state_history_manager_initialization():
    """StateHistoryManager initializes deques with zero vectors."""
    mgr = StateHistoryManager(sequence_length=4, n_observations=10)
    assert mgr.sequence_length == 4

    mgr.initialize_history(initial_states={"TL_1": [1.0] * 10}, agent_ids=["TL_1", "TL_2"])
    assert "TL_1" in mgr.history
    assert "TL_2" in mgr.history
    assert len(mgr.history["TL_1"]) == 4
    assert len(mgr.history["TL_1"][0]) == 10

    # Negative sequence_length fallback
    fallback_mgr = StateHistoryManager(sequence_length=-1, n_observations=5)
    assert fallback_mgr.sequence_length == 1


def test_episode_reporter_bulletin(mock_locale):
    """EpisodeReporter tallies maturity phases and logs school bulletin."""
    mock_maturity_mgr = MagicMock()
    mock_maturity_mgr.agent_maturity = {
        "TL_1": Maturity.CHILD,
        "TL_2": Maturity.TEEN,
        "TL_3": Maturity.ADULT,
    }
    mock_maturity_mgr.is_calibrated = True

    reporter = EpisodeReporter(locale_manager=mock_locale, maturity_manager=mock_maturity_mgr)

    with patch("core.system_reporter.SystemReporter.report_school_bulletin") as mock_report:
        reporter.report_episode_bulletin(
            agents={"TL_1": None, "TL_2": None, "TL_3": None},
            episode_counter=1,
            episode_total_reward=150.0,
        )
        assert mock_report.called


def test_guardian_communicator():
    """GuardianCommunicator sends state packages and receives veto signals."""
    mock_state_q = queue.Queue()
    mock_signal_q = queue.Queue()

    comm = GuardianCommunicator(mock_state_q, mock_signal_q)
    comm.send_state(current_states_dict={"TL_1": [0.5]}, done=False, mode="eval")

    package = mock_state_q.get_nowait()
    assert package[0] == {"TL_1": [0.5]}
    assert package[2] is False
    assert package[3] == "eval"

    # Put a veto map signal
    mock_signal_q.put({"type": "veto_map", "map": {"TL_1": {"veto_action": 0}}})
    vetos = comm.receive_vetos()
    assert vetos == {"TL_1": {"veto_action": 0}}


def test_asset_manager(mock_locale):
    """AssetManager creates specialist renderers and delegates rendering."""
    asset_mgr = AssetManager(mock_locale)
    assert asset_mgr.static_map_renderer is not None
    assert asset_mgr.heatmap_renderer is not None

    with patch.object(asset_mgr.heatmap_renderer, "create_heatmap_image_in_memory", return_value="base64str"):
        img = asset_mgr.create_heatmap_image_in_memory(map_data=(), congestion_data={})
        assert img == "base64str"


def test_service_manager(mock_locale):
    """ServiceManager manages process lifecycles and clean shutdown."""
    service_mgr = ServiceManager(mock_locale)
    mock_guardian_p = MagicMock()
    mock_guardian_p.is_alive.return_value = True
    mock_xai_p = MagicMock()
    mock_xai_p.is_alive.return_value = True

    service_mgr.guardian_worker_process = mock_guardian_p
    service_mgr.xai_worker_process = mock_xai_p

    service_mgr.stop_all_services()
    assert mock_guardian_p.terminate.called
    assert mock_xai_p.terminate.called
