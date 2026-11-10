# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import configparser
from unittest.mock import MagicMock
import pytest

from core.enums import Maturity
from maturity.maturity_manager import MaturityManager
from promotion.performance_margin_calculator import PerformanceMarginCalculator
from promotion.promotion_evaluator import PromotionEvaluator


def test_calculate_margin_formula():
    # v_real = 20.0, v_limit = 50.0 -> inefficiency = 1 - 0.4 = 0.6
    # occupancy = 0.2 -> free_space = 1 - 0.2 = 0.8
    # raw_margin = 0.25 * 0.6 * 0.8 * 100% = 12.0%
    margin = PerformanceMarginCalculator.calculate_margin(
        v_real=20.0,
        v_limit=50.0,
        occupancy=0.20,
        coupling_k=0.25,
    )
    assert margin == pytest.approx(12.0, abs=0.01)


def test_calculate_margin_bounds():
    # Lower bound test: almost no inefficiency, high occupancy
    low_margin = PerformanceMarginCalculator.calculate_margin(
        v_real=50.0,
        v_limit=50.0,
        occupancy=0.99,
        min_margin=3.0,
        max_margin=25.0,
    )
    assert low_margin == 3.0

    # Upper bound test: zero speed, zero occupancy
    high_margin = PerformanceMarginCalculator.calculate_margin(
        v_real=0.0,
        v_limit=60.0,
        occupancy=0.0,
        coupling_k=0.5,  # Boosted K to test clamp
        min_margin=3.0,
        max_margin=25.0,
    )
    assert high_margin == 25.0


def test_calculate_margin_zero_speed_limit():
    margin = PerformanceMarginCalculator.calculate_margin(
        v_real=10.0,
        v_limit=0.0,
        occupancy=0.5,
    )
    assert margin == PerformanceMarginCalculator.DEFAULT_MARGIN_PERCENT


def test_calculate_from_topology():
    # Case 1: None net
    assert PerformanceMarginCalculator.calculate_from_topology(None) == PerformanceMarginCalculator.DEFAULT_MARGIN_PERCENT

    # Case 2: Net with edges
    mock_edge1 = MagicMock()
    mock_edge1.getSpeed.return_value = 13.89  # 50 km/h
    mock_edge2 = MagicMock()
    mock_edge2.getSpeed.return_value = 16.67  # 60 km/h

    mock_net = MagicMock()
    mock_net.getEdges.return_value = [mock_edge1, mock_edge2]

    margin = PerformanceMarginCalculator.calculate_from_topology(mock_net)
    assert 3.0 <= margin <= 25.0


def test_calculate_from_childhood_telemetry():
    # Case 1: None conn
    assert PerformanceMarginCalculator.calculate_from_childhood_telemetry(None) == PerformanceMarginCalculator.DEFAULT_MARGIN_PERCENT

    # Case 2: Mock conn with row: mean_speed=5.0, speed_limit=13.89, occupancy=0.30
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchone.return_value = (5.0, 13.89, 0.30)

    margin = PerformanceMarginCalculator.calculate_from_childhood_telemetry(mock_conn, scenario_name="grid_test")
    assert 3.0 <= margin <= 25.0
    mock_cursor.execute.assert_called_once()

    # Case 3: Mock conn with empty result
    mock_cursor.fetchone.return_value = None
    margin_empty = PerformanceMarginCalculator.calculate_from_childhood_telemetry(mock_conn)
    assert margin_empty == PerformanceMarginCalculator.DEFAULT_MARGIN_PERCENT


def test_apply_if_enabled_respects_flag():
    mock_mgr = MagicMock()

    # Disabled via dict
    applied = PerformanceMarginCalculator.apply_if_enabled(mock_mgr, 12.5, {"auto_performance_margin_enabled": False})
    assert applied is False
    mock_mgr.set_performance_margin.assert_not_called()

    # Enabled via dict
    applied = PerformanceMarginCalculator.apply_if_enabled(mock_mgr, 12.5, {"auto_performance_margin_enabled": True})
    assert applied is True
    mock_mgr.set_performance_margin.assert_called_once_with(12.5)

    # ConfigParser support
    config = configparser.ConfigParser()
    config.add_section("MATURITY")
    config.set("MATURITY", "auto_performance_margin_enabled", "True")

    mock_mgr.reset_mock()
    applied_cfg = PerformanceMarginCalculator.apply_if_enabled(mock_mgr, 14.2, config)
    assert applied_cfg is True
    mock_mgr.set_performance_margin.assert_called_once_with(14.2)


def test_maturity_manager_and_evaluator_integration():
    mock_locale = MagicMock()
    mock_locale.get_string.side_effect = lambda k, **kw: k

    mgr = MaturityManager(
        settings={"performance_check_window": 5}, locale_manager=mock_locale, baseline={"mean_reward": -100.0}
    )

    # Dynamically update margin to 15.0%
    mgr.set_performance_margin(15.0)

    assert mgr.performance_margin == pytest.approx(1.15)
    assert mgr.baseline_target == pytest.approx(-115.0)
    assert mgr.promotion_evaluator.performance_margin_percent == pytest.approx(15.0)
