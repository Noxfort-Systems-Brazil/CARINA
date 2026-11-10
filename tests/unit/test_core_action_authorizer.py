# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from unittest.mock import MagicMock

import pytest

from core.action_authorizer import ActionAuthorizer
from core.enums import Maturity


@pytest.fixture
def mock_locale():
    lm = MagicMock()
    lm.get_string.side_effect = lambda key, fallback=None, **kwargs: fallback or key
    return lm


def test_action_authorizer_child(mock_locale):
    """Child agents must never be authorized to act (observation-only)."""
    authorizer = ActionAuthorizer(settings={}, locale_manager=mock_locale)
    authorized, reason = authorizer.is_action_authorized("TL_1", Maturity.CHILD, sim_time=100.0)
    assert authorized is False
    assert "Criança" in reason or "observação" in reason


def test_action_authorizer_adult(mock_locale):
    """Adult agents must always be authorized to act."""
    authorizer = ActionAuthorizer(settings={}, locale_manager=mock_locale)
    authorized, reason = authorizer.is_action_authorized("TL_1", Maturity.ADULT, sim_time=100.0)
    assert authorized is True
    assert "Adulto" in reason or "Autorizado" in reason


def test_action_authorizer_teen_default_offpeak(mock_locale):
    """Teen agents with fallback traffic profile should be authorized off-peak."""
    authorizer = ActionAuthorizer(settings={}, locale_manager=mock_locale)
    # T=3600 is 01:00 AM (offpeak)
    authorized, reason = authorizer.is_action_authorized("TL_1", Maturity.TEEN, sim_time=3600.0)
    assert authorized is True


def test_action_authorizer_teen_peak_restriction(mock_locale):
    """Teen agents with a configured peak profile must be blocked during peak hours."""
    # Day 0 (Monday), 8:00 AM is peak
    profiles = {0: {"8": "peak", "9": "peak", "14": "low"}}
    authorizer = ActionAuthorizer(settings={}, locale_manager=mock_locale, traffic_profiles=profiles)

    # 8:00 AM (8 * 3600 = 28800s)
    authorized_peak, reason_peak = authorizer.is_action_authorized("TL_1", Maturity.TEEN, sim_time=28800.0)
    assert authorized_peak is False
    assert "pico" in reason_peak.lower()

    # 2:00 PM (14 * 3600 = 50400s)
    authorized_offpeak, reason_offpeak = authorizer.is_action_authorized("TL_1", Maturity.TEEN, sim_time=50400.0)
    assert authorized_offpeak is True


def test_action_authorizer_unknown_maturity(mock_locale):
    """Any unhandled maturity state must fail closed."""
    authorizer = ActionAuthorizer(settings={}, locale_manager=mock_locale)
    authorized, reason = authorizer.is_action_authorized("TL_1", "SUPER_ADULT", sim_time=100.0)
    assert authorized is False
