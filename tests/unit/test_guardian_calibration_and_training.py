# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Unit & PyTorch verification tests for GuardianAgent safe CHILD-only off-policy training,
topology-aware edge slicing & physical capacity scaling, F2 quantile calibration,
Noisy-OR fusion, maturity freezing, and checkpoint persistence.
"""

import configparser
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import torch
import torch.nn as nn

from src.agents.guardian_agent import GuardianAgent
from src.engine.online_pae_trainer import OnlinePAETrainer
from src.engine.state_extractor import StateExtractor
from src.manager.cycle_manager import CycleManager
from src.safety.guardian_checkpoint_service import GuardianCheckpointService
from src.safety.guardian_risk_calibrator import GuardianRiskCalibrator
from src.safety.guardian_shadow_trainer import GuardianShadowTrainer

IS_REAL_TORCH = isinstance(getattr(nn, "Linear", None), type)


def _make_settings() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    cfg["GUARDIAN_AGENT"] = {
        "learning_rate": "0.001",
        "gamma": "0.90",
        "batch_size": "8",
        "memory_size": "256",
        "epsilon_start": "1.0",
        "epsilon_end": "0.05",
        "epsilon_decay": "30000",
    }
    cfg["GUARDIAN_REWARDS"] = {
        "correct_action": "42.0",
        "punish_inaction": "-88.0",
        "correct_inaction": "7.0",
        "punish_false_alarm": "-12.0",
    }
    return cfg


def _make_locale() -> MagicMock:
    lm = MagicMock()
    lm.get_string.side_effect = lambda key, default=None, **kwargs: default if default is not None else key
    return lm


def test_edge_only_saturation_ignores_phase_ped_and_aggregator_tails():
    """Saturation slicing strictly uses incoming edges and respects physical road capacity."""
    calibrator = GuardianRiskCalibrator(edge_feature_dim=3, edge_capacities=[20.0])
    # 3 edge features (calm street: occ=0.12, speed=0.80, queue=0.10) + active phase + ped + 24 aggregator peaks
    polluted_vec = np.array(
        [0.12, 0.80, 0.10] + [1.0, 0.0, 1.0] + [0.98] * 24,
        dtype=np.float32,
    )
    assert calibrator.extract_saturation(polluted_vec) == pytest.approx(0.12, abs=1e-5)

    # Short urban block (capacity = 5 veh): raw queue 0.20 (4 veh) = 80% physical saturation!
    short_cal = GuardianRiskCalibrator(edge_feature_dim=3, edge_capacities=[5.0])
    short_vec = np.array([0.40, 0.30, 0.20, 1.0, 0.0, 0.0], dtype=np.float32)
    assert short_cal.extract_saturation(short_vec) == pytest.approx(0.80, abs=1e-5)

    # Long arterial avenue (capacity = 60 veh): raw queue 0.90 (18 veh) = 30% physical fill, no false alarm
    long_cal = GuardianRiskCalibrator(edge_feature_dim=3, edge_capacities=[60.0])
    long_vec = np.array([0.25, 0.60, 0.90, 1.0, 0.0, 0.0], dtype=np.float32)
    assert long_cal.extract_saturation(long_vec) == pytest.approx(0.30, abs=1e-5)


def test_kinematic_horizon_projection_and_stationary_lockup():
    """Steady lockup returns 1.0 (not 0.75) and rising congestion projects over yellow + all_red."""
    cal = GuardianRiskCalibrator(clearance_horizon_sec=6.0, step_dt_sec=1.0, edge_feature_dim=3)
    steady_lockup = [np.array([1.0, 0.0, 1.0, 1.0], dtype=np.float32) for _ in range(4)]
    assert cal.compute_kinematic_risk(steady_lockup, []) == pytest.approx(1.0)

    # Ramp from 0.50 -> 0.65 over 3s (dS/dt = +0.05/s); 6s clearance adds +0.30 -> projects to 0.95
    rising = [
        np.array([0.50, 0.5, 0.1, 1.0], dtype=np.float32),
        np.array([0.55, 0.4, 0.1, 1.0], dtype=np.float32),
        np.array([0.60, 0.3, 0.1, 1.0], dtype=np.float32),
        np.array([0.65, 0.2, 0.1, 1.0], dtype=np.float32),
    ]
    assert cal.compute_kinematic_risk(rising, []) == pytest.approx(0.95, abs=1e-4)


def test_noisy_or_mutes_untrained_child_d3qn_and_prevents_dilution():
    """Untrained CHILD D3QN cannot trigger false alarms, and physical spillback cannot be averaged away."""
    cal = GuardianRiskCalibrator(spillback_floor=0.80)
    cal.child_learning_active = True
    cal.is_calibrated = False

    # Confused D3QN screaming 0.99 on empty road is muted in CHILD
    assert cal.fuse_risks(kinematic_risk=0.05, neural_prob=0.99, pae_risk=None) == pytest.approx(0.05, abs=1e-4)

    # Optimistic D3QN saying 0.01 cannot dilute an actual physical spillback (0.85)
    assert cal.fuse_risks(kinematic_risk=0.85, neural_prob=0.01, pae_risk=0.10) >= 0.85

    # PAE reliability drops automatically when reconstruction MSE degrades
    assert cal.compute_pae_reliability(pae_mse=0.50, log_var_mean=0.0) < cal.compute_pae_reliability(
        pae_mse=0.005, log_var_mean=-2.0
    )


def test_state_extractor_computes_edge_capacities_and_feature_dim():
    """StateExtractor derives incoming edge feature slice & capacities directly from sumolib graph."""
    extractor = StateExtractor(_make_locale())

    edge_a = MagicMock()
    edge_a.getID.return_value = "eA"
    edge_a.getLength.return_value = 70.0
    edge_a.getLaneNumber.return_value = 1  # capacity = 10.0

    edge_b = MagicMock()
    edge_b.getID.return_value = "eB"
    edge_b.getLength.return_value = 210.0
    edge_b.getLaneNumber.return_value = 2  # capacity = 60.0

    lane_a = MagicMock()
    lane_a.getID.return_value = "eA_0"
    lane_a.getEdge.return_value = edge_a
    lane_a.getFromLane.return_value = lane_a

    lane_b = MagicMock()
    lane_b.getID.return_value = "eB_0"
    lane_b.getEdge.return_value = edge_b
    lane_b.getFromLane.return_value = lane_b

    mock_tls = MagicMock()
    mock_tls.getID.return_value = "TL1"
    mock_tls.getConnections.return_value = [[lane_b], [lane_a]]
    mock_tls.getPrograms.return_value = {}

    mock_net = MagicMock()
    mock_net.getTrafficLights.return_value = [mock_tls]

    with patch("sumolib.net.readNet", return_value=mock_net):
        extractor.load_topology("/fake/map.net.xml")

    assert extractor.get_edge_feature_dim("TL1") == 6
    assert extractor.get_edge_capacities("TL1") == pytest.approx([10.0, 60.0])


@pytest.mark.skipif(not IS_REAL_TORCH, reason="Requires real PyTorch autograd to verify off-policy QR-D3QN updates")
def test_shadow_trainer_child_training_calibration_and_permanent_freeze():
    """Verifies full lifecycle: CHILD shadow collection & updates -> TEEN F2 calibration & weight freeze."""
    settings = _make_settings()
    lm = _make_locale()
    guardian = GuardianAgent(
        aiconfig=settings["GUARDIAN_AGENT"],
        traffic_rules_config=settings["GUARDIAN_AGENT"],
        locale_manager=lm,
        shared_pae=None,
        n_observations=6,
        edge_feature_dim=3,
        edge_capacities=[10.0],
    )
    trainer = GuardianShadowTrainer(
        settings=settings, device=torch.device("cpu"), updates_per_cycle=4, min_replay_warmup=8
    )

    phase_enum = SimpleNamespace(name="CHILD")
    maturity_mgr = SimpleNamespace(agent_maturity={"TL1": phase_enum}, get_agent_phase=lambda k: phase_enum)
    fake_agent = SimpleNamespace(memory=SimpleNamespace(states=[]))
    agents = {"TL1": fake_agent}
    guardians = {"TL1": guardian}

    # Feed 24 HFT steps alternating safe KEEP, protective KEEP, safe CHANGE, and spillback CHANGE
    for step in range(24):
        if step < 10:
            vec = np.array([0.15, 0.85, 0.05, 1.0, 0.0, 0.0], dtype=np.float32)
            stage = 0
        elif step == 10:
            # High pressure held safely
            vec = np.array([0.75, 0.25, 0.35, 1.0, 0.0, 0.0], dtype=np.float32)
            stage = 0
        elif step == 15:
            # Stage changed directly into severe spillback!
            vec = np.array([0.92, 0.05, 0.45, 0.0, 1.0, 0.0], dtype=np.float32)
            stage = 2
        elif step == 20:
            # Calm stage change
            vec = np.array([0.20, 0.80, 0.05, 1.0, 0.0, 0.0], dtype=np.float32)
            stage = 0
        else:
            sat = 0.72 if 11 <= step < 15 else 0.25
            vec = np.array([sat, 0.50, 0.20, 1.0, 0.0, 0.0], dtype=np.float32)
            stage = 2 if 15 <= step < 20 else 0

        fake_agent.memory.states.append(vec)
        trainer.observe_step(
            traffic_data={"emergency_brakes": 0, "teleports": 0},
            agents=agents,
            guardians=guardians,
            current_stages={"TL1": stage},
            maturity_manager=maturity_mgr,
            sim_time=step * 0.25,
            pae_mse=0.02,
        )

    assert len(guardian.memory) == 23
    rewards_recorded = guardian.memory.rewards[: len(guardian.memory)].squeeze(-1).tolist()
    actions_recorded = guardian.memory.actions[: len(guardian.memory)].squeeze(-1).tolist()
    assert -88.0 in rewards_recorded  # punish_inaction on CHANGE into spillback
    assert 7.0 in rewards_recorded  # correct_inaction on safe CHANGE
    assert 42.0 in rewards_recorded  # correct_action on holding pressure safely
    assert 1 in actions_recorded and 0 in actions_recorded
    assert guardian.calibrator.child_learning_active is True

    # Ensure boosted PER priority on rare CHANGE transitions
    change_idx = actions_recorded.index(1)
    assert float(guardian.memory.priorities[change_idx].item()) >= 4.0

    # Train one CHILD cycle and assert weights genuinely move
    before_weights = [p.detach().clone() for p in guardian.policy_net.parameters()]
    losses = trainer.train_active_child_guardians(guardians, maturity_mgr)
    assert "TL1" in losses and guardian.steps_done == 4
    assert any(not torch.allclose(b, a) for b, a in zip(before_weights, guardian.policy_net.parameters()))
    assert guardian.policy_net.training is False

    # Populate clear calibration contrast and promote CHILD -> TEEN
    for i in range(40):
        guardian.calibrator.record_child_observation(margin=-3.0, spread=2.0, spillback_flag=False)
        guardian.calibrator.record_child_observation(margin=4.0, spread=2.0, spillback_flag=True)

    phase_enum.name = "TEEN"
    frozen_ids = trainer.sync_maturation_and_freeze(guardians, maturity_mgr)
    assert frozen_ids == ["TL1"]
    assert guardian.is_frozen is True
    assert guardian.calibrator.is_calibrated is True
    assert guardian.calibrator.child_learning_active is False
    assert 0.45 <= guardian.calibrator.calibrated_threshold <= 0.80
    assert all(not p.requires_grad for p in guardian.policy_net.parameters())

    # Attempting TEEN/ADULT observation + training must leave memory, steps_done, and weights untouched
    frozen_snap = [p.detach().clone() for p in guardian.policy_net.parameters()]
    steps_at_freeze = guardian.steps_done
    mem_len_at_freeze = len(guardian.memory)

    fake_agent.memory.states.append(np.array([0.90, 0.10, 0.45, 0.0, 1.0, 0.0], dtype=np.float32))
    trainer.observe_step({}, agents, guardians, {"TL1": 2}, maturity_mgr, 99.0)
    assert trainer.train_active_child_guardians(guardians, maturity_mgr) == {}
    assert guardian.steps_done == steps_at_freeze
    assert len(guardian.memory) == mem_len_at_freeze
    assert all(torch.equal(b, a) for b, a in zip(frozen_snap, guardian.policy_net.parameters()))


@pytest.mark.skipif(not IS_REAL_TORCH, reason="Requires real PyTorch state_dict serialization roundtrip")
def test_guardian_checkpoint_and_cycle_manager_persistence(tmp_path):
    """CycleManager and GuardianCheckpointService persist and restore frozen calibrated state."""
    settings = _make_settings()
    lm = _make_locale()
    guardian = GuardianAgent(
        aiconfig=settings["GUARDIAN_AGENT"],
        traffic_rules_config=settings["GUARDIAN_AGENT"],
        locale_manager=lm,
        n_observations=4,
        edge_feature_dim=3,
        edge_capacities=[12.0],
    )
    guardian.steps_done = 77
    guardian.calibrator.logit_scale = 2.4
    guardian.calibrator.logit_bias = -0.35
    guardian.calibrator.reference_spread = 3.1
    guardian.calibrator.calibrated_threshold = 0.58
    guardian.calibrator.d3qn_reliability = 0.89
    guardian.calibrator.is_calibrated = True
    guardian.freeze_for_deployment()

    mock_maturity = SimpleNamespace(
        agent_maturity={"TL_CKPT": SimpleNamespace(name="TEEN")},
        check_and_promote_agents=MagicMock(return_value=False),
    )
    mock_agent = MagicMock()
    mock_agent.memory = []
    trainer = GuardianShadowTrainer(settings=settings, device=torch.device("cpu"))
    cycle_mgr = CycleManager(
        maturity_manager=mock_maturity,
        pipe_conn=MagicMock(),
        settings=settings,
        guardian_trainer=trainer,
        guardians={"TL_CKPT": guardian},
    )

    with patch("manager.cycle_manager.get_base_output_dir", return_value=str(tmp_path)):
        cycle_mgr._save_checkpoints({"TL_CKPT": mock_agent})

    expected_ckpt = tmp_path / "results" / "hft_live_session" / "checkpoints" / "guardian_TL_CKPT.pth"
    assert expected_ckpt.exists()

    restored = GuardianAgent(
        aiconfig=settings["GUARDIAN_AGENT"],
        traffic_rules_config=settings["GUARDIAN_AGENT"],
        locale_manager=lm,
        n_observations=4,
    )
    loaded = GuardianCheckpointService.load_guardian(
        "TL_CKPT",
        restored,
        checkpoints_dir=str(expected_ckpt.parent),
        device=torch.device("cpu"),
    )
    assert loaded is True
    assert restored.steps_done == 77
    assert restored.is_frozen is True
    assert restored.calibrator.is_calibrated is True
    assert restored.calibrator.logit_scale == pytest.approx(2.4)
    assert restored.calibrator.calibrated_threshold == pytest.approx(0.58)
    assert restored.calibrator.edge_capacities == pytest.approx([12.0])


def test_online_pae_trainer_tracks_ema_prediction_mse():
    """OnlinePAETrainer exposes smoothed `last_prediction_mse` after updates and clears on reset()."""
    trainer = OnlinePAETrainer(settings=MagicMock(), agent_manager=MagicMock())
    assert trainer.last_prediction_mse is None
    trainer._record_pae_mse(0.5)
    assert trainer.last_prediction_mse == pytest.approx(0.5)
    trainer._record_pae_mse(0.0)
    assert trainer.last_prediction_mse == pytest.approx(0.4)
    trainer.reset()
    assert trainer.last_prediction_mse is None
