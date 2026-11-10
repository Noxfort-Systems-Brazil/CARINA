# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import configparser
from unittest.mock import MagicMock
import pytest

from engine.reward_calculator import RewardCalculator
from engine.reward_weights_calculator import RewardWeightsCalculator
from ui.cards.reward_weights_card import RewardWeightsCard


def test_calculate_weights_formula():
    # 150m at 13.89 m/s (50 km/h) -> tau = 150 / 13.89 ~ 10.80s
    w_wait, w_flow = RewardWeightsCalculator.calculate_weights(
        mean_length=150.0,
        mean_speed_limit=13.89,
        alpha=1.0,
    )
    assert w_wait == -1.0
    assert w_flow == pytest.approx(10.80, abs=0.01)


def test_calculate_weights_bounds():
    # Lower clamp: 10m at 20 m/s -> tau = 0.5s -> clamped to 2.0
    w_wait, low_flow = RewardWeightsCalculator.calculate_weights(
        mean_length=10.0,
        mean_speed_limit=20.0,
        min_flow=2.0,
        max_flow=25.0,
    )
    assert w_wait == -1.0
    assert low_flow == 2.0

    # Upper clamp: 1000m at 10 m/s -> tau = 100s -> clamped to 25.0
    w_wait, high_flow = RewardWeightsCalculator.calculate_weights(
        mean_length=1000.0,
        mean_speed_limit=10.0,
        min_flow=2.0,
        max_flow=25.0,
    )
    assert w_wait == -1.0
    assert high_flow == 25.0


def test_calculate_weights_zero_or_invalid():
    w_wait, w_flow = RewardWeightsCalculator.calculate_weights(
        mean_length=150.0,
        mean_speed_limit=0.0,
    )
    assert w_wait == RewardWeightsCalculator.DEFAULT_WAITING_WEIGHT
    assert w_flow == RewardWeightsCalculator.DEFAULT_FLOW_WEIGHT


def test_calculate_from_topology():
    # Case 1: None net
    assert RewardWeightsCalculator.calculate_from_topology(None) == (
        RewardWeightsCalculator.DEFAULT_WAITING_WEIGHT,
        RewardWeightsCalculator.DEFAULT_FLOW_WEIGHT,
    )

    # Case 2: Net with edges
    mock_edge1 = MagicMock()
    mock_edge1.getLength.return_value = 120.0
    mock_edge1.getSpeed.return_value = 13.89

    mock_edge2 = MagicMock()
    mock_edge2.getLength.return_value = 180.0
    mock_edge2.getSpeed.return_value = 13.89

    mock_net = MagicMock()
    mock_net.getEdges.return_value = [mock_edge1, mock_edge2]

    w_wait, w_flow = RewardWeightsCalculator.calculate_from_topology(mock_net)
    assert w_wait == -1.0
    assert 2.0 <= w_flow <= 25.0
    assert w_flow == pytest.approx(150.0 / 13.89, abs=0.01)


def test_apply_if_enabled_respects_flag():
    mock_target = MagicMock()

    # Disabled via dict
    applied = RewardWeightsCalculator.apply_if_enabled(
        target=mock_target,
        weights=(-1.0, 12.0),
        settings={"auto_reward_weights_enabled": False},
    )
    assert applied is False
    mock_target.set_reward_weights.assert_not_called()

    # Enabled via dict
    settings_dict = {"auto_reward_weights_enabled": True}
    applied = RewardWeightsCalculator.apply_if_enabled(
        target=mock_target,
        weights=(-1.0, 12.0),
        settings=settings_dict,
    )
    assert applied is True
    mock_target.set_reward_weights.assert_called_once_with(-1.0, 12.0)
    assert settings_dict["weight_waiting_time"] == "-1.0"
    assert settings_dict["weight_flow"] == "12.0"

    # Enabled via ConfigParser
    config = configparser.ConfigParser()
    config.add_section("REWARD_WEIGHTS")
    config.set("REWARD_WEIGHTS", "auto_reward_weights_enabled", "True")

    mock_target.reset_mock()
    applied_cfg = RewardWeightsCalculator.apply_if_enabled(
        target=mock_target,
        weights=(-1.0, 14.5),
        settings=config,
    )
    assert applied_cfg is True
    mock_target.set_reward_weights.assert_called_once_with(-1.0, 14.5)
    assert config.getfloat("REWARD_WEIGHTS", "weight_waiting_time") == -1.0
    assert config.getfloat("REWARD_WEIGHTS", "weight_flow") == 14.5


def test_reward_calculator_set_reward_weights():
    mock_locale = MagicMock()
    mock_locale.get_string.side_effect = lambda k, **kw: k

    config = configparser.ConfigParser()
    config.add_section("REWARD_WEIGHTS")
    config.set("REWARD_WEIGHTS", "weight_waiting_time", "-2.0")
    config.set("REWARD_WEIGHTS", "weight_flow", "2.0")

    calc = RewardCalculator(config, mock_locale)
    assert calc.reward_weights["waiting_time"] == -2.0
    assert calc.reward_weights["flow"] == 2.0

    calc.set_reward_weights(-1.0, 11.2)
    assert calc.reward_weights["waiting_time"] == -1.0
    assert calc.reward_weights["flow"] == 11.2


def test_reward_weights_card_ui():
    mock_locale = MagicMock()
    mock_locale.get_string.side_effect = lambda k, **kw: k

    # 1. Initialized with auto enabled
    card = RewardWeightsCard(initial_values={
        "auto_reward_weights_enabled": True,
        "weight_waiting_time": "-1.0",
        "weight_flow": "10.0",
    })

    assert card.sw_auto_reward_weights.value is True
    assert card.tf_weight_waiting_time.disabled is True
    assert card.tf_weight_flow.disabled is True

    # 2. Toggle to manual
    card.sw_auto_reward_weights.value = False
    card._on_auto_reward_weights_toggle(None)
    assert card.tf_weight_waiting_time.disabled is False
    assert card.tf_weight_flow.disabled is False

    # 3. get_values / set_values
    vals = card.get_values()
    assert vals["auto_reward_weights_enabled"] is False
    assert vals["weight_waiting_time"] == "-1.0"
    assert vals["weight_flow"] == "10.0"

    card.set_values({
        "auto_reward_weights_enabled": True,
        "weight_waiting_time": "-2.0",
        "weight_flow": "15.0",
    })
    assert card.sw_auto_reward_weights.value is True
    assert card.tf_weight_waiting_time.disabled is True
    assert card.tf_weight_flow.disabled is True
    assert card.tf_weight_waiting_time.value == "-2.0"
    assert card.tf_weight_flow.value == "15.0"

    # 4. update_translations
    card.update_translations(mock_locale)
    assert card.title_text.value == "settings_view.reward_weights_card.title"
