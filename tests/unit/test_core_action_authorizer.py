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

# File: tests/unit/test_core_action_authorizer.py
# Author: Gabriel Moraes
# Date: September 2026

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
