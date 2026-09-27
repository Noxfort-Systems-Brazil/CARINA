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

# File: tests/unit/test_engine_cycle_and_timer.py
# Author: Gabriel Moraes
# Date: September 2026

from unittest.mock import MagicMock, patch

import pytest

from core.enums import Maturity
from engine.cycle_manager import CycleManager
from engine.step_timer import StepTimer


def test_step_timer_hft_mode():
    """StepTimer records phase latencies in HFT mode."""
    timer = StepTimer(log_step_progress=False)

    timer.start_step()
    timer.start_phase()
    timer.stop_phase("extraction")
    assert timer.t_extraction >= 0.0

    timer.start_phase()
    timer.stop_phase("inference")
    assert timer.t_inference >= 0.0

    # Stop invalid phase should not crash
    timer.start_phase()
    timer.stop_phase("unknown_phase")

    with patch("logging.info") as mock_log:
        timer.log_and_finish_step(guardian_vetoed=False, log_progress=True)
        assert mock_log.called


def test_step_timer_episode_mode():
    """StepTimer records markers in Episode mode and formats logging."""
    timer = StepTimer(log_step_progress=True, freq=1)

    timer.mark_total_start()
    timer.mark_decision_start()
    timer.mark_decision_end()
    assert timer.t_decision_end >= timer.t_decision_start

    timer.mark_auth_start()
    timer.mark_auth_end()
    assert timer.t_auth_end >= timer.t_auth_start

    with patch("logging.info") as mock_info:
        timer.log_if_needed(1)
        assert mock_info.called


def test_cycle_manager_evaluate_cycle(tmp_path):
    """CycleManager aggregates metrics, triggers promotion check, and sends update via pipe."""
    mock_maturity_mgr = MagicMock()
    mock_maturity_mgr.check_and_promote_agents.return_value = True
    mock_maturity_mgr.agent_maturity = {"TL_1": Maturity.TEEN}

    mock_pipe = MagicMock()

    cycle_mgr = CycleManager(mock_maturity_mgr, mock_pipe)

    mock_agent = MagicMock()
    mock_agent.memory = [1, 2, 3]
    agents = {"TL_1": mock_agent}

    accumulated_metrics = {
        "TL_1": {
            "count": 2,
            "reward_sum": 200.0,
            "entropy_sum": 0.4,
        }
    }

    with patch("engine.cycle_manager.get_base_output_dir", return_value=str(tmp_path)):
        cycle_mgr.evaluate_cycle(
            step_counter=10,
            agents=agents,
            accumulated_metrics=accumulated_metrics,
            mfd_efficiency=0.85,
        )

    assert mock_maturity_mgr.check_and_promote_agents.called
    assert mock_agent.save_checkpoint.called
    assert mock_pipe.send.called
    # Memory should be cleared to prevent RAM leak
    assert len(mock_agent.memory) == 0
    # Accumulated metrics cleared for next cycle
    assert len(accumulated_metrics) == 0
