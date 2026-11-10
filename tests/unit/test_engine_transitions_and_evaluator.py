# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from unittest.mock import MagicMock, patch

import pytest

from engine.evaluator import ValidationEvaluator
from manager.stage_transition_manager import StageTransitionManager


def test_stage_transition_manager_yellow_advance():
    """StageTransitionManager automatically advances yellow stage when duration exceeds yellow_time."""
    mock_extractor = MagicMock()
    mock_extractor.tl_green_stages = {"TL_1": [0]}  # 0 is green, 1 is yellow
    mock_extractor.tl_stage_codes = {"TL_1": {0: "G", 1: "y", 2: "r"}}

    mock_supervisor = MagicMock()
    mock_supervisor._last_stage_change_time = {"TL_1": 10.0}

    manager = StageTransitionManager(mock_extractor, mock_supervisor)
    current_stages = {"TL_1": 1}  # Currently in yellow (1)

    # Simulation time is 10.0 + yellow_time + 1.0 -> should advance to red (2)
    manager.auto_advance_transitions(sim_time=10.0 + manager.yellow_time + 1.0, current_stages=current_stages)
    assert current_stages["TL_1"] == 2
    assert mock_supervisor._last_stage_change_time["TL_1"] > 10.0


def test_stage_transition_manager_update_estimated_stage():
    """StageTransitionManager updates estimated stage index on demand."""
    mock_extractor = MagicMock()
    mock_extractor.tl_stage_codes = {"TL_1": {0: "G", 1: "y", 2: "r"}}
    mock_supervisor = MagicMock()
    mock_supervisor._last_stage_change_time = {}

    manager = StageTransitionManager(mock_extractor, mock_supervisor)
    current_stages = {"TL_1": 0}

    manager.update_estimated_stage("TL_1", current_stage_idx=0, sim_time=25.0, current_stages=current_stages)
    assert current_stages["TL_1"] == 1
    assert mock_supervisor._last_stage_change_time["TL_1"] == 25.0


def test_validation_evaluator_execution():
    """ValidationEvaluator runs evaluation episodes without learning."""
    mock_settings = MagicMock()
    mock_settings.getint.side_effect = lambda sec, key, fallback=None: 4 if "seq" in key else 10

    evaluator = ValidationEvaluator(mock_settings)

    mock_agent = MagicMock()
    mock_agent.device = "cpu"
    mock_action = MagicMock()
    mock_action.item.return_value = 0
    mock_agent.choose_action.return_value = (mock_action, None, None, None)

    agents = {"TL_1": mock_agent}

    mock_env = MagicMock()
    mock_env.get_global_state.return_value = {"TL_1": [0.1, 0.2]}
    # Step returns next_states, rewards, done
    mock_env.step.return_value = ({"TL_1": [0.1, 0.2]}, {"TL_1": 5.0}, True)

    avg_reward = evaluator.evaluate(agents, mock_env, num_episodes=1)
    assert avg_reward == 5.0
    assert mock_agent.policy_net.eval.called
    assert mock_agent.policy_net.train.called


def test_stage_transition_manager_apply_software_transitions():
    """StageTransitionManager applies transitions only for actions where action == 0."""
    mock_extractor = MagicMock()
    mock_extractor.tl_stage_codes = {
        "TL_1": {0: "G", 1: "y", 2: "r"},
        "TL_2": {0: "G", 1: "y", 2: "r"},
    }
    mock_supervisor = MagicMock()
    mock_supervisor._last_stage_change_time = {}

    manager = StageTransitionManager(mock_extractor, mock_supervisor)
    current_stages = {"TL_1": 0, "TL_2": 0}

    # TL_1 requests change (0), TL_2 requests hold (1)
    actions = {"TL_1": 0, "TL_2": 1}
    manager.apply_software_transitions(actions, sim_time=30.0, current_stages=current_stages)

    assert current_stages["TL_1"] == 1  # transitioned to next stage
    assert current_stages["TL_2"] == 0  # untouched


def test_agent_evaluator_evaluate_fleet():
    """AgentEvaluator evaluate_fleet processes all agents and aggregates FleetDecisions."""
    from engine.agent_evaluator import AgentEvaluator, FleetDecisions

    evaluator = AgentEvaluator(
        state_extractor=MagicMock(),
        input_preprocessor=MagicMock(),
        reward_computer=MagicMock(),
        action_authorizer=MagicMock(),
        action_supervisor=MagicMock(),
        maturity_manager=MagicMock(),
        locale_manager=MagicMock(),
    )

    evaluator.evaluate_agent = MagicMock(
        side_effect=[
            (1, "ADULT", False, 10.0, 0.1, {"lane1": "G"}),
            (0, "CHILD", True, 5.0, 0.2, {"lane2": "r"}),
        ]
    )

    agents = {"TL_1": MagicMock(), "TL_2": MagicMock()}
    current_stages = {"TL_1": 0, "TL_2": 1}
    guardians = {"TL_1": MagicMock(), "TL_2": MagicMock()}

    decisions = evaluator.evaluate_fleet(
        agents=agents,
        current_stages=current_stages,
        traffic_data={"edges": {}},
        edges_data={},
        sim_time=15.0,
        guardians=guardians,
        step_timer=MagicMock(),
    )

    assert isinstance(decisions, FleetDecisions)
    assert decisions.actions == {"TL_1": 1, "TL_2": 0}
    assert decisions.step_reward_sum == 15.0
    assert decisions.guardian_vetoed_any is True
    assert decisions.maturity_info == {"TL_1": "ADULT", "TL_2": "CHILD"}
    assert decisions.metrics_delta["TL_1"] == (10.0, 0.1)
    assert decisions.metrics_delta["TL_2"] == (5.0, 0.2)


def test_agent_evaluator_evp_and_empty_state():
    import numpy as np
    from engine.agent_evaluator import AgentEvaluator
    from core.enums import Maturity

    se = MagicMock()
    se.get_phase_lane_states.return_value = {"lane1": "G"}
    se.extract_state.return_value = np.array([])  # Empty state

    evaluator = AgentEvaluator(
        state_extractor=se,
        input_preprocessor=MagicMock(),
        reward_computer=MagicMock(),
        action_authorizer=MagicMock(),
        action_supervisor=MagicMock(),
        maturity_manager=MagicMock(),
        locale_manager=MagicMock(),
    )

    # Test _get_evp_preemption_state
    with patch("src.engine.evp_preemption_evaluator.EvpPreemptionEvaluator.get_evp_preemption_state", return_value="CORREDOR:VTR_01"):
        assert evaluator._get_evp_preemption_state("TL_1") == "CORREDOR:VTR_01"

    # Test empty state extraction early return
    step_timer = MagicMock()
    action, maturity, vetoed, rew, ent, lanes = evaluator.evaluate_agent(
        tl_id="TL_1",
        agent=MagicMock(),
        current_stage_idx=0,
        traffic_data={"tls_telemetry": {"TL_1": {"active_ped_calls": 1}}},
        edges_data={},
        sim_time=10.0,
        guardian=None,
        step_timer=step_timer,
    )
    assert action is None
    assert vetoed is False
    assert rew == 0.0

    # Test with precomputed_state_data
    mock_agent = MagicMock()
    mock_agent.choose_action.return_value = (MagicMock(item=lambda: 1), MagicMock(), MagicMock(), MagicMock(item=lambda: 0.1))
    evaluator.action_authorizer.is_action_authorized.return_value = (True, "OK")
    evaluator.reward_computer.calculate.return_value = 1.0
    action2, _, _, _, _, _ = evaluator.evaluate_agent(
        tl_id="TL_1",
        agent=mock_agent,
        current_stage_idx=0,
        traffic_data={},
        edges_data={},
        sim_time=10.0,
        guardian=None,
        step_timer=step_timer,
        precomputed_state_data=(np.array([1.0]), MagicMock(), np.array([1.0])),
    )
    assert action2 == 1



def test_agent_evaluator_evaluate_agent_evp_preemption():
    import numpy as np
    import torch
    from engine.agent_evaluator import AgentEvaluator
    from core.enums import Maturity

    se = MagicMock()
    se.get_phase_lane_states.return_value = {"lane1": "G"}
    se.extract_state.return_value = np.array([0.1, 0.2])

    ip = MagicMock()
    state_tensor = torch.zeros((1, 2))
    ip.prepare_tensor.return_value = (state_tensor, np.array([0.1, 0.2]))

    rc = MagicMock()
    rc.calculate.return_value = 5.0

    aa = MagicMock()
    aa.is_action_authorized.return_value = (True, "OK")

    mm = MagicMock()
    mm.agent_maturity = {"TL_1": Maturity.ADULT}

    lm = MagicMock()
    lm.get_string.return_value = "Change"

    agent = MagicMock()
    agent.device = "cpu"
    # Action 0 = change stage
    action_idx = torch.tensor([0])
    agent.choose_action.return_value = (action_idx, torch.tensor([0.0]), torch.tensor([1.0]), torch.tensor([0.5]))
    agent.evaluate.return_value = (torch.tensor([0.0]), torch.tensor([1.0]), torch.tensor([0.5]))

    evaluator = AgentEvaluator(
        state_extractor=se,
        input_preprocessor=ip,
        reward_computer=rc,
        action_authorizer=aa,
        action_supervisor=MagicMock(),
        maturity_manager=mm,
        locale_manager=lm,
        db_manager=MagicMock(),
    )

    with patch.object(evaluator, "_get_evp_preemption_state", return_value="EVP:Ambulance"):
        step_timer = MagicMock()
        action, maturity, vetoed, rew, ent, lanes = evaluator.evaluate_agent(
            tl_id="TL_1",
            agent=agent,
            current_stage_idx=0,
            traffic_data={},
            edges_data={},
            sim_time=12.0,
            guardian=None,
            step_timer=step_timer,
        )

    assert vetoed is True
    assert action == 1  # Forced to keep stage (1) by EVP preemption
    assert rew == 5.0
    assert ent == 0.5


def test_agent_evaluator_evaluate_agent_guardian_veto_and_allow():
    import numpy as np
    import torch
    from engine.agent_evaluator import AgentEvaluator
    from core.enums import Maturity

    se = MagicMock()
    se.get_phase_lane_states.return_value = {"lane1": "G"}
    se.extract_state.return_value = np.array([0.1, 0.2])
    se.tl_stage_codes = {"TL_1": {0: "G", 1: "y"}}
    se.tl_stage_durations = {"TL_1": {0: 10.0, 1: 3.0}}


    ip = MagicMock()
    state_tensor = torch.zeros((1, 2))
    ip.prepare_tensor.return_value = (state_tensor, np.array([0.1, 0.2]))

    rc = MagicMock()
    rc.calculate.return_value = 8.0

    aa = MagicMock()
    aa.is_action_authorized.return_value = (True, "OK")

    mm = MagicMock()
    mm.agent_maturity = {"TL_1": Maturity.ADULT}

    asup = MagicMock()
    asup._last_stage_change_time = {"TL_1": 0.0}

    agent = MagicMock()
    agent.device = "cpu"
    agent.choose_action.return_value = (torch.tensor([0]), torch.tensor([0.0]), torch.tensor([1.0]), torch.tensor([0.3]))
    agent.evaluate.return_value = (torch.tensor([0.0]), torch.tensor([1.0]), torch.tensor([0.3]))

    evaluator = AgentEvaluator(
        state_extractor=se,
        input_preprocessor=ip,
        reward_computer=rc,
        action_authorizer=aa,
        action_supervisor=asup,
        maturity_manager=mm,
        locale_manager=MagicMock(),
    )


    guardian = MagicMock()
    guardian.ACTION_KEEP_STAGE = 1
    # 1. Guardian VETO
    guardian.select_action.return_value = (guardian.ACTION_KEEP_STAGE, "Safety risk")

    with patch.object(evaluator, "_get_evp_preemption_state", return_value=None):
        action, maturity, vetoed, rew, ent, lanes = evaluator.evaluate_agent(
            tl_id="TL_1",
            agent=agent,
            current_stage_idx=0,
            traffic_data={"timestamp": 123.4},
            edges_data={},
            sim_time=15.0,
            guardian=guardian,
            step_timer=MagicMock(),
        )

    assert vetoed is True
    assert action == 1

    # 2. Guardian ALLOW
    guardian.select_action.return_value = (0, "Safe")
    with patch.object(evaluator, "_get_evp_preemption_state", return_value=None):
        action, maturity, vetoed, rew, ent, lanes = evaluator.evaluate_agent(
            tl_id="TL_1",
            agent=agent,
            current_stage_idx=0,
            traffic_data={"timestamp": 123.4},
            edges_data={},
            sim_time=15.0,
            guardian=guardian,
            step_timer=MagicMock(),
        )

    assert vetoed is False
    assert action == 0


def test_agent_evaluator_evaluate_fleet_batched_pae():
    import numpy as np
    import torch
    from engine.agent_evaluator import AgentEvaluator

    se = MagicMock()
    se.extract_state.return_value = np.array([0.5, 0.5])

    ip = MagicMock()
    t1 = torch.zeros((1, 4))
    ip.prepare_tensor.return_value = (t1, np.array([0.5, 0.5]))

    pae = MagicMock()
    pae.device.type = "cpu"
    pae.standardize_sequence.side_effect = lambda t: t
    pae.encode.return_value = torch.ones((1, 8))

    agent1 = MagicMock()
    agent1.shared_pae = pae

    evaluator = AgentEvaluator(
        state_extractor=se,
        input_preprocessor=ip,
        reward_computer=MagicMock(),
        action_authorizer=MagicMock(),
        action_supervisor=MagicMock(),
        maturity_manager=MagicMock(),
        locale_manager=MagicMock(),
    )

    evaluator.evaluate_agent = MagicMock(return_value=(0, "ADULT", False, 1.0, 0.1, {}))

    # Test successful PAE batch encoding
    decisions = evaluator.evaluate_fleet(
        agents={"TL_1": agent1},
        current_stages={"TL_1": 0},
        traffic_data={},
        edges_data={},
        sim_time=10.0,
        guardians={},
        step_timer=MagicMock(),
    )
    assert len(decisions.actions) == 1
    assert pae.encode.called

    # Test PAE batch encoding fallback on exception
    pae.encode.side_effect = RuntimeError("PAE fail")
    decisions = evaluator.evaluate_fleet(
        agents={"TL_1": agent1},
        current_stages={"TL_1": 0},
        traffic_data={},
        edges_data={},
        sim_time=10.0,
        guardians={},
        step_timer=MagicMock(),
    )
    assert len(decisions.actions) == 1


