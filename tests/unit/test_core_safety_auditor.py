# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from unittest.mock import MagicMock, patch

import pytest

from core.safety_auditor import SafetyAuditor


def test_safety_auditor_non_zero_action():
    """Non-zero action (keep phase) is not a phase change request and bypasses audit."""
    auditor = SafetyAuditor(guardian_agent=None)
    mock_env = MagicMock()
    action, vetoed = auditor.audit(suggested_action=1, tl_id="TL_1", augmented_state=[], environment=mock_env)
    assert action == 1
    assert vetoed is False


def test_safety_auditor_symbolic_guardian_veto():
    """Phase change request (0) vetoed by Guardian symbolic rules returns (1, True)."""
    mock_guardian = MagicMock()
    mock_guardian.symbolic_audit.return_value = (0, "Vetoed: min green not satisfied")

    auditor = SafetyAuditor(guardian_agent=mock_guardian)

    mock_env = MagicMock()
    mock_env.conn = None
    mock_env.action_supervisor = None
    mock_env.state_extractor.tl_stage_codes = {"TL_1": {0: "G", 1: "Y"}}
    mock_env.state_extractor.tl_stage_durations = {"TL_1": {0: 10.0}}

    action, vetoed = auditor.audit(suggested_action=0, tl_id="TL_1", augmented_state=[], environment=mock_env)
    assert action == 1
    assert vetoed is True


def test_safety_auditor_neural_spillback_veto():
    """High spillback risk (>0.8) from neural veto map triggers a veto."""
    mock_guardian = MagicMock()
    mock_guardian.symbolic_audit.return_value = (1, "Approved")

    auditor = SafetyAuditor(guardian_agent=mock_guardian)

    mock_env = MagicMock()
    mock_env.conn = None
    mock_env.action_supervisor = None
    mock_env.state_extractor.tl_stage_codes = {"TL_1": {0: "G", 1: "Y"}}
    mock_env.state_extractor.tl_stage_durations = {"TL_1": {0: 10.0}}

    veto_map = {"TL_1": 0.95}  # Above 0.8 threshold
    action, vetoed = auditor.audit(
        suggested_action=0, tl_id="TL_1", augmented_state=[], environment=mock_env, latest_veto_map=veto_map
    )
    assert action == 1
    assert vetoed is True


def test_safety_auditor_approval():
    """When both symbolic barrier and neural spillback clear, action is approved."""
    mock_guardian = MagicMock()
    mock_guardian.symbolic_audit.return_value = (1, "Approved")

    auditor = SafetyAuditor(guardian_agent=mock_guardian)

    mock_env = MagicMock()
    mock_env.conn = None
    mock_env.action_supervisor = None
    mock_env.state_extractor.tl_stage_codes = {"TL_1": {0: "G", 1: "Y"}}
    mock_env.state_extractor.tl_stage_durations = {"TL_1": {0: 10.0}}

    veto_map = {"TL_1": 0.3}  # Safe risk
    action, vetoed = auditor.audit(
        suggested_action=0, tl_id="TL_1", augmented_state=[], environment=mock_env, latest_veto_map=veto_map
    )
    assert action == 0
    assert vetoed is False


def test_safety_auditor_exploratory_veto_reason():
    """Exploratory veto in veto_map records exploratory reason in last_veto_reasons."""
    mock_guardian = MagicMock()
    mock_guardian.symbolic_audit.return_value = (1, "Approved")

    auditor = SafetyAuditor(guardian_agent=mock_guardian)

    mock_env = MagicMock()
    mock_env.conn = None
    mock_env.action_supervisor = None
    mock_env.state_extractor.tl_stage_codes = {"TL_1": {0: "G", 1: "Y"}}
    mock_env.state_extractor.tl_stage_durations = {"TL_1": {0: 10.0}}

    veto_map = {"TL_1": {"risk": 1.0, "is_exploratory": True}}
    action, vetoed = auditor.audit(
        suggested_action=0, tl_id="TL_1", augmented_state=[], environment=mock_env, latest_veto_map=veto_map
    )
    assert action == 1
    assert vetoed is True
    assert "exploratória" in auditor.last_veto_reasons["TL_1"].lower()


def test_safety_auditor_neural_veto_reason():
    """Neural veto in veto_map records D3QN neural reason in last_veto_reasons."""
    mock_guardian = MagicMock()
    mock_guardian.symbolic_audit.return_value = (1, "Approved")

    auditor = SafetyAuditor(guardian_agent=mock_guardian)

    mock_env = MagicMock()
    mock_env.conn = None
    mock_env.action_supervisor = None
    mock_env.state_extractor.tl_stage_codes = {"TL_1": {0: "G", 1: "Y"}}
    mock_env.state_extractor.tl_stage_durations = {"TL_1": {0: 10.0}}

    veto_map = {"TL_1": {"risk": 1.0, "is_exploratory": False}}
    action, vetoed = auditor.audit(
        suggested_action=0, tl_id="TL_1", augmented_state=[], environment=mock_env, latest_veto_map=veto_map
    )
    assert action == 1
    assert vetoed is True
    assert "d3qn" in auditor.last_veto_reasons["TL_1"].lower() or "neural" in auditor.last_veto_reasons["TL_1"].lower()


def test_safety_auditor_max_green_overrides_neural_veto():
    """When green duration exceeds max_green_time, stage change (0) is allowed despite high neural spillback risk."""
    mock_guardian = MagicMock()
    mock_guardian.symbolic_audit.return_value = (1, "Approved")

    auditor = SafetyAuditor(guardian_agent=mock_guardian)

    mock_env = MagicMock()
    mock_env.conn = MagicMock()
    mock_env.conn.simulation.getTime.return_value = 100.0
    mock_env.conn.trafficlight.getPhase.return_value = 0
    mock_env.action_supervisor = MagicMock()
    # Started at t=30.0, current t=100.0 => duration = 70.0s > 60.0s max green ceiling
    mock_env.action_supervisor._last_stage_change_time = {"TL_1": 30.0}
    mock_env.state_extractor.tl_stage_codes = {"TL_1": {0: "G", 1: "Y"}}
    mock_env.state_extractor.tl_stage_durations = {"TL_1": {0: 10.0}}

    veto_map = {"TL_1": {"risk": 1.0, "is_exploratory": False}}
    action, vetoed = auditor.audit(
        suggested_action=0, tl_id="TL_1", augmented_state=[], environment=mock_env, latest_veto_map=veto_map
    )
    # Must override the neural veto to allow stage transition
    assert action == 0
    assert vetoed is False
    assert "teto máximo" in auditor.last_veto_reasons["TL_1"].lower()


def test_safety_auditor_telemetry_error_triggers_failsafe_veto(caplog):
    """When connection telemetry raises an error during a phase switch request, conservative fail-safe veto is applied."""
    mock_guardian = MagicMock()
    auditor = SafetyAuditor(guardian_agent=mock_guardian)

    mock_env = MagicMock()
    mock_env.conn = MagicMock()
    mock_env.conn.simulation.getTime.side_effect = RuntimeError("TraCI socket disconnected")

    action, vetoed = auditor.audit(suggested_action=0, tl_id="TL_1", augmented_state=[], environment=mock_env)
    assert action == 1
    assert vetoed is True
    assert "fail-safe" in auditor.last_veto_reasons["TL_1"].lower()
    assert any("Falha ao consultar fase/tempo" in rec.message for rec in caplog.records)

