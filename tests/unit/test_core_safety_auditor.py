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

# File: tests/unit/test_core_safety_auditor.py
# Author: Gabriel Moraes
# Date: September 2026

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
