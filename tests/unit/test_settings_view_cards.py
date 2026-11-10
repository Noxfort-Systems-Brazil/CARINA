# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from unittest.mock import MagicMock
import configparser
import pytest


def test_units_section_get_set_values():
    from ui.section.units_section import UnitsSection

    initial_values = {"xai_speed_unit": "km/h"}
    section = UnitsSection(initial_values)

    assert section.get_values()["xai_speed_unit"] == "km/h"

    section.set_values({"xai_speed_unit": "imperial"})
    assert section.get_values()["xai_speed_unit"] == "imperial"

    mock_locale_manager = MagicMock()
    mock_locale_manager.get_string.side_effect = lambda key, default=None: f"Mock_{key}"
    section.update_translations(mock_locale_manager)
    assert section.lbl_units_title.value == "Mock_settings_view.formatting_card.units_title"


def test_piloting_school_card_auto_calculation_and_toggle():
    from ui.cards.piloting_school_card import PilotingSchoolCard

    initial_settings = {
        "auto_pacing_enabled": False,
        "child_phase_episodes": "1",
        "teen_phase_min_episodes": "1",
        "auto_performance_margin_enabled": False,
        "performance_margin": "10.0",
    }
    card = PilotingSchoolCard(initial_settings)
    mock_page = MagicMock()
    card.page = mock_page

    assert card.tf_child_phase_episodes.value == "1"
    assert card.tf_child_phase_episodes.disabled is False
    assert card.tf_teen_phase_min_episodes.value == "1"
    assert card.tf_teen_phase_min_episodes.disabled is False

    # Toggle auto pacing ON
    card.sw_auto_pacing.value = True
    card._on_auto_pacing_toggle(None)

    # Values should be computed automatically and disabled
    child_val = card.tf_child_phase_episodes.value
    teen_val = card.tf_teen_phase_min_episodes.value
    assert int(child_val) > 0
    assert card.tf_child_phase_episodes.disabled is True
    assert int(teen_val) > 0
    assert card.tf_teen_phase_min_episodes.disabled is True

    # Toggle auto margin ON
    card.sw_auto_performance_margin.value = True
    card._on_auto_margin_toggle(None)
    margin_val = card.tf_performance_margin.value
    assert float(margin_val) > 0
    assert card.tf_performance_margin.disabled is True

    # Card values
    vals = card.get_values()
    assert vals["auto_pacing_enabled"] is True
    assert vals["child_phase_episodes"] == child_val
    assert vals["teen_phase_min_episodes"] == teen_val
    assert vals["auto_performance_margin_enabled"] is True

    # Pacing informative container verification
    assert card.pacing_info_container is not None
    assert card.calculated_steps > 0
    assert card.calculated_min_episodes > 0
    assert str(card.calculated_steps) in card.lbl_steps_per_episode.value
    assert str(card.calculated_min_episodes) in card.lbl_inviolable_floor.value


def test_piloting_school_card_manual_safety_floor_validation():
    from ui.cards.piloting_school_card import PilotingSchoolCard

    card = PilotingSchoolCard({"auto_pacing_enabled": False, "child_phase_episodes": "10", "teen_phase_min_episodes": "5"})
    mock_page = MagicMock()
    card.page = mock_page

    # Should detect input below safety floor
    min_floor = card.calculated_min_episodes
    assert min_floor > 0
    assert card.tf_child_phase_episodes.error_text is not None
    assert card.tf_teen_phase_min_episodes.error_text is not None

    # When retrieving values, safety floor must be enforced (clamped)
    values = card.get_values()
    assert int(values["child_phase_episodes"]) >= min_floor
    assert int(values["teen_phase_min_episodes"]) >= min_floor

    # Setting value above floor removes error
    card.tf_child_phase_episodes.value = str(min_floor + 50)
    card._on_episode_input_change(None)
    assert not card.tf_child_phase_episodes.error_text
    assert card.get_values()["child_phase_episodes"] == str(min_floor + 50)

    # Translations update
    mock_lm = MagicMock()
    mock_lm.get_string.side_effect = lambda key, default=None, **kwargs: default if default else key
    card.update_translations(mock_lm)
    assert card.tf_child_phase_episodes.helper_text is not None
    assert str(min_floor) in card.tf_child_phase_episodes.helper_text



def test_reward_weights_card_auto_calculation_and_toggle():
    from ui.cards.reward_weights_card import RewardWeightsCard

    initial_settings = {
        "auto_reward_weights_enabled": False,
        "weight_waiting_time": "-2.0",
        "weight_flow": "2.0",
    }
    card = RewardWeightsCard(initial_settings)
    mock_page = MagicMock()
    card.page = mock_page

    assert card.tf_weight_waiting_time.value == "-2.0"
    assert card.tf_weight_waiting_time.disabled is False
    assert card.tf_weight_flow.value == "2.0"
    assert card.tf_weight_flow.disabled is False

    # Toggle auto weights ON
    card.sw_auto_reward_weights.value = True
    card._on_auto_reward_weights_toggle(None)

    # Values should be computed automatically and disabled
    flow_val = card.tf_weight_flow.value
    assert card.tf_weight_waiting_time.value == "-1.0"
    assert card.tf_weight_waiting_time.disabled is True
    assert float(flow_val) > 0
    assert card.tf_weight_flow.disabled is True

    vals = card.get_values()
    assert vals["auto_reward_weights_enabled"] is True
    assert vals["weight_waiting_time"] == "-1.0"
    assert vals["weight_flow"] == flow_val


def test_settings_handler_saves_directly_to_disk(tmp_path):
    from ui.handlers.settings_handler import SettingsHandler

    ini_file = tmp_path / "settings.ini"
    config = configparser.ConfigParser()
    config.add_section("MATURITY")
    config.set("MATURITY", "child_phase_episodes", "1")
    config.set("MATURITY", "teen_phase_min_episodes", "1")
    config.set("MATURITY", "auto_pacing_enabled", "False")
    config.add_section("REWARD_WEIGHTS")
    config.set("REWARD_WEIGHTS", "weight_waiting_time", "-2.0")
    config.set("REWARD_WEIGHTS", "weight_flow", "2.0")
    with open(ini_file, "w") as f:
        config.write(f)

    handler = SettingsHandler(config_path=str(ini_file))

    new_settings = {
        "auto_pacing_enabled": True,
        "child_phase_episodes": 37,
        "teen_phase_min_episodes": 145,
        "weight_waiting_time": -1.0,
        "weight_flow": 10.0,
    }

    payload = handler.prepare_settings_for_save(new_settings)

    # Verify changes were immediately written to disk
    read_cfg = configparser.ConfigParser()
    read_cfg.read(str(ini_file))
    assert read_cfg.get("MATURITY", "child_phase_episodes") == "37"
    assert read_cfg.get("MATURITY", "teen_phase_min_episodes") == "145"
    assert read_cfg.get("MATURITY", "auto_pacing_enabled") == "True"
    assert read_cfg.get("REWARD_WEIGHTS", "weight_waiting_time") == "-1.0"
    assert read_cfg.get("REWARD_WEIGHTS", "weight_flow") == "10.0"
    assert payload["child_phase_episodes"] == 37


def test_piloting_school_card_defaults_to_auto_enabled_and_can_be_disabled():
    from ui.cards.piloting_school_card import PilotingSchoolCard

    # Card initialized with empty settings must default to auto enabled (True)
    card = PilotingSchoolCard({})
    mock_page = MagicMock()
    card.page = mock_page

    assert card.sw_auto_pacing.value is True
    assert card.sw_auto_performance_margin.value is True
    assert card.tf_child_phase_episodes.disabled is True
    assert card.tf_teen_phase_min_episodes.disabled is True
    assert card.tf_performance_margin.disabled is True

    # User disables auto pacing in options
    card.sw_auto_pacing.value = False
    card._on_auto_pacing_toggle(None)
    assert card.tf_child_phase_episodes.disabled is False
    assert card.tf_teen_phase_min_episodes.disabled is False

    # User disables auto performance margin in options
    card.sw_auto_performance_margin.value = False
    card._on_auto_margin_toggle(None)
    assert card.tf_performance_margin.disabled is False

    vals = card.get_values()
    assert vals["auto_pacing_enabled"] is False
    assert vals["auto_performance_margin_enabled"] is False


def test_reward_weights_card_defaults_to_auto_enabled_and_can_be_disabled():
    from ui.cards.reward_weights_card import RewardWeightsCard

    # Card initialized with empty settings must default to auto enabled (True)
    card = RewardWeightsCard({})
    mock_page = MagicMock()
    card.page = mock_page

    assert card.sw_auto_reward_weights.value is True
    assert card.tf_weight_waiting_time.disabled is True
    assert card.tf_weight_flow.disabled is True

    # User disables auto reward weights in options
    card.sw_auto_reward_weights.value = False
    card._on_auto_reward_weights_toggle(None)
    assert card.tf_weight_waiting_time.disabled is False
    assert card.tf_weight_flow.disabled is False

    vals = card.get_values()
    assert vals["auto_reward_weights_enabled"] is False

