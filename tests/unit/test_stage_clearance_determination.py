# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Unit tests for StateExtractor fallback durations and clearance red determination."""

from unittest.mock import MagicMock, patch
import pytest

from src.engine.state_extractor import StateExtractor
from src.manager.stage_transition_manager import StageTransitionManager


def test_fallback_durations_and_clearance_determination():
    """Tests if StateExtractor fallback durations are correct, and StageTransitionManager distinguishes clearance red properly."""
    mock_locale = MagicMock()
    mock_locale.get_string.return_value = "Mocked String"

    extractor = StateExtractor(locale_manager=mock_locale)

    mock_net = MagicMock()
    mock_tls = MagicMock()
    mock_tls.getID.return_value = "TL_MOCK"
    mock_tls.getConnections.return_value = []
    mock_tls.getPrograms.return_value = {}  # Trigger fallback
    mock_net.getTrafficLights.return_value = [mock_tls]

    with patch("sumolib.net.readNet", return_value=mock_net):
        extractor.load_topology("mock_path.net.xml")

    assert "TL_MOCK" in extractor.tl_stage_durations
    # Stage 2 should be clearance (3.0s), stage 5 should be normal red (10.0s)
    assert extractor.tl_stage_durations["TL_MOCK"][2] == 3.0
    assert extractor.tl_stage_durations["TL_MOCK"][5] == 10.0

    mock_supervisor = MagicMock()
    stm = StageTransitionManager(state_extractor=extractor, action_supervisor=mock_supervisor)

    stage_codes = extractor.tl_stage_codes["TL_MOCK"]

    # Stage 2 logic test (Clearance Red)
    prev_state_string = stage_codes.get(1, "").upper()
    stage_durations = extractor.tl_stage_durations["TL_MOCK"]
    default_duration_2 = stage_durations.get(2, 0.0)
    is_clearance_2 = ("Y" in prev_state_string) and (default_duration_2 <= stm.all_red_time)
    assert is_clearance_2 is True

    # Stage 5 logic test (Normal Red)
    prev_state_string_5 = stage_codes.get(4, "").upper()
    default_duration_5 = stage_durations.get(5, 0.0)
    is_clearance_5 = ("Y" in prev_state_string_5) and (default_duration_5 <= stm.all_red_time)
    assert is_clearance_5 is False
