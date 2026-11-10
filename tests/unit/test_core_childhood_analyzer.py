# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import tempfile
from unittest.mock import MagicMock

import pytest

from core.childhood_analyzer import ChildhoodAnalyzer


@pytest.fixture
def mock_locale():
    lm = MagicMock()
    lm.get_string.side_effect = lambda key, fallback=None, **kwargs: fallback or key
    return lm


def test_childhood_analyzer_cache_save_and_load(mock_locale):
    """Tests saving and loading analysis cache."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mock_settings = MagicMock()
        mock_settings.getint.return_value = 2
        mock_settings.__contains__.side_effect = lambda k: False

        analyzer = ChildhoodAnalyzer(mock_settings, tmpdir, mock_locale)
        assert analyzer.analysis_episodes == 2
        assert analyzer.check_cache() is False

        profiles = {"day_0": {"8": "peak"}}
        baseline = {"avg_reward": 150.0}

        analyzer.save_to_cache(profiles, baseline)
        assert analyzer.check_cache() is True

        loaded_profiles, loaded_baseline = analyzer.load_from_cache()
        assert loaded_profiles == profiles
        assert loaded_baseline == baseline


def test_childhood_analyzer_run_analysis_empty(mock_locale):
    """Tests run_analysis with empty metrics returning fallback profiles."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mock_settings = MagicMock()
        mock_settings.getint.return_value = 1
        mock_settings.__contains__.side_effect = lambda k: False

        analyzer = ChildhoodAnalyzer(mock_settings, tmpdir, mock_locale)
        profiles, baseline = analyzer.run_analysis([])
        assert isinstance(profiles, dict)
        assert isinstance(baseline, dict)
