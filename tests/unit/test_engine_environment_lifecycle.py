# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import configparser
from unittest.mock import MagicMock, patch
import pytest

from src.engine.environment import SumoEnvironment


@pytest.fixture
def base_env():
    settings = configparser.ConfigParser()
    settings.add_section("AI_TRAINING")
    settings.set("AI_TRAINING", "episode_max_steps", "5")

    lm = MagicMock()
    lm.get_string.side_effect = lambda k, **kw: f"mock_str_{k}"

    return SumoEnvironment(settings=settings, locale_manager=lm)


def test_environment_init(base_env):
    assert base_env.episode_max_steps == 5
    assert base_env.current_episode_steps == 0
    assert base_env.conn is None
    assert base_env.state_extractor is None
    assert base_env.reward_calculator is None
    assert base_env.action_supervisor is None


def test_environment_connect_and_close(base_env):
    mock_conn = MagicMock()

    with patch("src.engine.environment.StateExtractor") as MockSE, \
         patch("src.engine.environment.RewardCalculator") as MockRC, \
         patch("src.engine.environment.ActionSupervisor") as MockAS:
        base_env.connect(mock_conn)

        assert base_env.conn is mock_conn
        assert base_env.state_extractor is not None
        assert base_env.reward_calculator is not None
        assert base_env.action_supervisor is not None

    base_env.close()
    assert base_env.conn is None


def test_environment_connect_exception(base_env):
    mock_conn = MagicMock()
    with patch("src.engine.environment.StateExtractor", side_effect=RuntimeError("Init err")):
        base_env.connect(mock_conn)
        assert base_env.scenario_path == "mock_str_environment.connect.unknown_scenario"


def test_environment_reset_no_conn(base_env):
    base_env.reset()
    assert base_env.current_episode_steps == 0


def test_environment_reset_with_conn(base_env):
    base_env.conn = MagicMock()
    base_env.action_supervisor = MagicMock()
    base_env.current_episode_steps = 3
    base_env._last_batched_data = {"test": 1}

    base_env.reset()

    base_env.action_supervisor.reset.assert_called_once()
    assert base_env.current_episode_steps == 0
    assert base_env._last_batched_data == {}


def test_environment_step_no_conn(base_env):
    states, rewards, done = base_env.step({"tl1": 0})
    assert states == {}
    assert rewards == {}
    assert done is True


def test_environment_step_no_batch_data(base_env):
    base_env.conn = MagicMock()
    base_env.conn.custom.get_batched_step_data.return_value = None

    states, rewards, done = base_env.step({"tl1": 0})
    assert states == {}
    assert rewards == {}
    assert done is True
    assert base_env.conn is None


def test_environment_step_normal_and_terminal(base_env):
    base_env.conn = MagicMock()
    base_env.action_supervisor = MagicMock()
    base_env.state_extractor = MagicMock()
    base_env.reward_calculator = MagicMock()

    base_env.state_extractor.get_global_state_from_batch.return_value = {"tl1": [1, 2, 3]}
    base_env.reward_calculator.calculate_rewards_from_batch.return_value = {"tl1": 1.5}

    batch_data = {
        "sim_min_expected_number": 1,
        "override_commands": {"cmd": 1},
        "active_overrides": {"tl1": "EMERGENCY"},
        "operation_mode": "MANUAL",
    }
    base_env.conn.custom.get_batched_step_data.return_value = batch_data

    # Step 1
    next_states, rewards, done = base_env.step({"tl1": 1})
    assert next_states["tl1"] == [1, 2, 3]
    assert next_states["override_commands"] == {"cmd": 1}
    assert next_states["active_overrides"] == {"tl1": "EMERGENCY"}
    assert next_states["operation_mode"] == "MANUAL"
    assert rewards == {"tl1": 1.5}
    assert done is False
    assert base_env.current_episode_steps == 1

    # Step 2: natural end
    batch_data_end = {"sim_min_expected_number": 0}
    base_env.conn.custom.get_batched_step_data.return_value = batch_data_end
    next_states, rewards, done = base_env.step({"tl1": 1})
    assert done is True


def test_environment_step_exception_handling(base_env):
    base_env.conn = MagicMock()
    base_env.conn.custom.get_batched_step_data.side_effect = RuntimeError("SUMO step fail")

    states, rewards, done = base_env.step({"tl1": 0})
    assert states == {}
    assert rewards == {}
    assert done is True
    assert base_env.conn is None


def test_environment_get_global_state(base_env):
    # No conn
    assert base_env.get_global_state() == {}

    # With conn but empty batch
    base_env.conn = MagicMock()
    base_env.conn.custom.get_batched_step_data.return_value = {}
    assert base_env.get_global_state() == {}

    # With normal batch
    base_env.state_extractor = MagicMock()
    base_env.state_extractor.get_global_state_from_batch.return_value = {"tl1": [0.1]}
    batch = {"operation_mode": "CENTRALIZED", "raw": [1, 2]}
    base_env.conn.custom.get_batched_step_data.return_value = batch

    state = base_env.get_global_state()
    assert state["tl1"] == [0.1]
    assert state["operation_mode"] == "CENTRALIZED"
    assert base_env._last_batched_data == batch

    # Exception in get_global_state
    base_env.conn.custom.get_batched_step_data.side_effect = RuntimeError("Conn err")
    assert base_env.get_global_state() == {}
    assert base_env.conn is None


def test_environment_delegation_helpers(base_env):
    # When state_extractor is None
    assert base_env.get_traffic_light_ids() == []
    assert base_env.get_observation_space_size_for_tl("tl1") == 0
    assert base_env.get_num_green_phases_for_tl("tl1") == 0

    # When state_extractor is present
    se = MagicMock()
    se.get_traffic_light_ids.return_value = ["tl1", "tl2"]
    se.get_observation_space_size_for_tl.return_value = 16
    se._get_green_phases_for_tl.return_value = 4
    base_env.state_extractor = se

    assert base_env.get_traffic_light_ids() == ["tl1", "tl2"]
    assert base_env.get_observation_space_size_for_tl("tl1") == 16
    assert base_env.get_num_green_phases_for_tl("tl1") == 4
