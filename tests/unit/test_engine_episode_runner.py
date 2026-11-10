# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import configparser
from unittest.mock import MagicMock, patch
import pytest

from src.engine.episode_runner import EpisodeRunner


def create_mock_settings(update_timestep=2048, log_step_progress=True, log_progress_frequency=1):
    settings = configparser.ConfigParser()
    settings.add_section("AI_TRAINING")
    settings.set("AI_TRAINING", "sequence_length", "4")
    settings.set("AI_TRAINING", "episode_max_steps", "10")
    if update_timestep is not None:
        settings.set("AI_TRAINING", "update_timestep", str(update_timestep))
    settings.add_section("LOGGING")
    settings.set("LOGGING", "log_step_progress", str(log_step_progress))
    settings.set("LOGGING", "log_progress_frequency", str(log_progress_frequency))
    return settings


@pytest.fixture
def base_components():
    lm = MagicMock()
    lm.get_string.side_effect = lambda k, **kw: f"mock_str_{k}"

    env = MagicMock()
    env.conn = MagicMock()
    env.conn.simulation.getTime.return_value = 12.0
    env.action_supervisor = MagicMock()

    pop_mgr = MagicMock()
    agent_mock = MagicMock()
    agent_mock.memory = [1, 2, 3]
    pop_mgr.agents = {"tl1": agent_mock}

    maturity_mgr = MagicMock()
    maturity_mgr.locale_manager = lm

    learning_coord = MagicMock()
    strategic_coord = MagicMock()
    strategic_coord.neighborhoods = {"tl1": ["tl2"]}

    childhood_analyzer = MagicMock()
    action_authorizer = MagicMock()

    return {
        "lm": lm,
        "env": env,
        "pop_mgr": pop_mgr,
        "maturity_mgr": maturity_mgr,
        "learning_coord": learning_coord,
        "strategic_coord": strategic_coord,
        "childhood_analyzer": childhood_analyzer,
        "action_authorizer": action_authorizer,
    }


def test_episode_runner_init_fallback(base_components):
    # Test fallback when update_timestep is not provided in settings
    settings = configparser.ConfigParser()
    settings.add_section("AI_TRAINING")

    with patch("src.database.database_manager.DatabaseManager", side_effect=RuntimeError("DB fail")):
        runner = EpisodeRunner(
            settings=settings,
            env=base_components["env"],
            population_manager=base_components["pop_mgr"],
            maturity_manager=base_components["maturity_mgr"],
            learning_coordinator=base_components["learning_coord"],
            strategic_coordinator=base_components["strategic_coord"],
            childhood_analyzer=base_components["childhood_analyzer"],
            action_authorizer=base_components["action_authorizer"],
            n_observations=8,
        )

    assert runner.update_timestep == 2048
    assert runner.db_manager is None
    assert runner.episode_max_steps == 5000


def test_episode_runner_run_empty_initial_state(base_components):
    settings = create_mock_settings()
    env = base_components["env"]
    env.get_global_state.return_value = {}

    runner = EpisodeRunner(
        settings=settings,
        env=env,
        population_manager=base_components["pop_mgr"],
        maturity_manager=base_components["maturity_mgr"],
        learning_coordinator=base_components["learning_coord"],
        strategic_coordinator=base_components["strategic_coord"],
        childhood_analyzer=base_components["childhood_analyzer"],
        action_authorizer=base_components["action_authorizer"],
        n_observations=8,
    )

    metrics = runner.run(episode_count=1)
    assert metrics == {}
    env.reset.assert_called_once()


def test_episode_runner_run_lost_connection(base_components):
    settings = create_mock_settings()
    env = base_components["env"]
    env.get_global_state.return_value = {"tl1": [0.1] * 8, "operation_mode": "AUTOMATIC"}
    env.conn = None

    runner = EpisodeRunner(
        settings=settings,
        env=env,
        population_manager=base_components["pop_mgr"],
        maturity_manager=base_components["maturity_mgr"],
        learning_coordinator=base_components["learning_coord"],
        strategic_coordinator=base_components["strategic_coord"],
        childhood_analyzer=base_components["childhood_analyzer"],
        action_authorizer=base_components["action_authorizer"],
        n_observations=8,
    )

    metrics = runner.run(episode_count=1)
    assert isinstance(metrics, dict)


def test_episode_runner_run_simulation_time_error(base_components):
    settings = create_mock_settings()
    env = base_components["env"]
    env.get_global_state.return_value = {"tl1": [0.1] * 8}
    env.conn = MagicMock()
    env.conn.simulation.getTime.side_effect = RuntimeError("SUMO disconnected")

    runner = EpisodeRunner(
        settings=settings,
        env=env,
        population_manager=base_components["pop_mgr"],
        maturity_manager=base_components["maturity_mgr"],
        learning_coordinator=base_components["learning_coord"],
        strategic_coordinator=base_components["strategic_coord"],
        childhood_analyzer=base_components["childhood_analyzer"],
        action_authorizer=base_components["action_authorizer"],
        n_observations=8,
    )

    metrics = runner.run(episode_count=1)
    assert isinstance(metrics, dict)


def test_episode_runner_run_simulation_conn_no_simulation(base_components):
    settings = create_mock_settings()
    env = base_components["env"]
    env.get_global_state.return_value = {"tl1": [0.1] * 8}
    env.conn = object()  # Has no simulation attribute

    runner = EpisodeRunner(
        settings=settings,
        env=env,
        population_manager=base_components["pop_mgr"],
        maturity_manager=base_components["maturity_mgr"],
        learning_coordinator=base_components["learning_coord"],
        strategic_coordinator=base_components["strategic_coord"],
        childhood_analyzer=base_components["childhood_analyzer"],
        action_authorizer=base_components["action_authorizer"],
        n_observations=8,
    )

    metrics = runner.run(episode_count=1)
    assert isinstance(metrics, dict)


def test_episode_runner_run_normal_cycle_and_vetos(base_components):
    settings = create_mock_settings(update_timestep=2)
    env = base_components["env"]
    initial_state = {"tl1": [0.1] * 8, "operation_mode": "AUTOMATIC"}
    env.get_global_state.return_value = initial_state

    # 1st step: done=False, 2nd step: done=True
    step_1_res = ({"tl1": [0.2] * 8, "override_states": {}}, {"tl1": 1.0}, False)
    step_2_res = ({"tl1": [0.3] * 8, "override_states": {}}, {"tl1": 2.0}, True)
    env.step.side_effect = [step_1_res, step_2_res]

    runner = EpisodeRunner(
        settings=settings,
        env=env,
        population_manager=base_components["pop_mgr"],
        maturity_manager=base_components["maturity_mgr"],
        learning_coordinator=base_components["learning_coord"],
        strategic_coordinator=base_components["strategic_coord"],
        childhood_analyzer=base_components["childhood_analyzer"],
        action_authorizer=base_components["action_authorizer"],
        n_observations=8,
    )

    # Mock decision coordinator return
    runner.decision_coordinator.get_coordinated_actions = MagicMock(
        return_value=(
            {"tl1": 0},
            {"tl1": {"entropy": 0.5, "state_sequence": [[0.1] * 8]}},
        )
    )
    runner.action_filter.filter_actions = MagicMock(return_value={"tl1": 0})
    runner.guardian_comm.receive_vetos = MagicMock(return_value={"tl1": [1]})

    metrics = runner.run(episode_count=1)

    assert env.step.call_count == 2
    assert base_components["learning_coord"].store_experience.call_count == 2
    assert base_components["learning_coord"].update_agents.call_count >= 1
    assert env.action_supervisor.update_vetos.called
    assert isinstance(metrics, dict)


def test_episode_runner_run_strategic_coord_error_and_invalid_next_state(base_components):
    settings = create_mock_settings()
    env = base_components["env"]
    env.get_global_state.return_value = {"tl1": [0.1] * 8}

    # step returns next_states_dict = None
    env.step.return_value = (None, {"tl1": 0.5}, False)

    base_components["strategic_coord"].update_if_needed.side_effect = RuntimeError("Strategic failure")

    runner = EpisodeRunner(
        settings=settings,
        env=env,
        population_manager=base_components["pop_mgr"],
        maturity_manager=base_components["maturity_mgr"],
        learning_coordinator=base_components["learning_coord"],
        strategic_coordinator=base_components["strategic_coord"],
        childhood_analyzer=base_components["childhood_analyzer"],
        action_authorizer=base_components["action_authorizer"],
        n_observations=8,
    )

    runner.decision_coordinator.get_coordinated_actions = MagicMock(return_value=({}, {}))
    metrics = runner.run(episode_count=1)
    assert isinstance(metrics, dict)
