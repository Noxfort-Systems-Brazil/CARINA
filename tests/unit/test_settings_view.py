# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Unit tests for SettingsView mounting, file picker registration, and discard behaviors."""

from unittest.mock import MagicMock
import configparser
import flet as ft
import pytest

from ui.cards.general_settings_card import GeneralSettingsCard
from ui.cards.report_formatting_card import ReportFormattingCard
from ui.cards.traffic_rules_card import TrafficRulesCard
from ui.handlers.settings_handler import SettingsHandler
from ui.views.settings_view import SettingsView


def test_settings_view_file_picker_registration():
    """
    Verifies that the logo file picker is successfully registered to the page overlay
    on mounting SettingsView, and that subsequent individual card did_mount calls
    do not register duplicates.
    """
    mock_locale_manager = MagicMock()
    mock_locale_manager.get_string.return_value = "Mock Text"
    mock_settings_client = MagicMock()

    initial_settings = {
        "xai_font_name": "Arial",
        "xai_font_size": 11,
        "xai_alignment": "justify",
        "xai_line_spacing": 1.15,
        "xai_margin_top": 1.0,
        "xai_margin_bottom": 1.0,
        "xai_margin_left": 1.0,
        "xai_margin_right": 1.0,
        "xai_report_title": "TEST REPORT",
        "xai_logo_path": "/some/path/logo.png",
        "xai_secretary_name": "Secretary",
        "xai_secretary_title": "Title",
        "xai_agency_name": "Agency",
        "xai_department_name": "Department",
        "xai_block_order": "header,content",
    }

    formatting_card = ReportFormattingCard(initial_settings)
    warning_text = ft.Text("warning")

    tab_definitions = [
        {
            "icon": ft.Icons.PRINT_ROUNDED,
            "title_key": "settings_view.tab_formatting",
            "default_title": "Formatação",
            "cards": [formatting_card],
        }
    ]

    view = SettingsView(
        locale_manager=mock_locale_manager,
        settings_client=mock_settings_client,
        tab_definitions=tab_definitions,
        warning_text_ref=warning_text,
    )

    mock_page = MagicMock()
    mock_page.overlay = []

    view.page = mock_page
    formatting_card.page = mock_page

    # Trigger mount
    view.did_mount()

    # Assert picker was registered
    assert formatting_card.logo_file_picker in mock_page.overlay

    # Verify individual card did_mount checks to prevent duplicates
    count_before = len(mock_page.overlay)
    formatting_card.did_mount()
    assert len(mock_page.overlay) == count_before


def test_settings_view_discard_changes_reverts_values_and_theme():
    mock_lm = MagicMock()
    mock_lm.get_string.return_value = "Mock"
    mock_client = MagicMock()

    initial = {
        "theme_dark": True,
        "language": "pt_br",
        "min_green_time": "10",
        "yellow_time": "3",
    }

    general_card = GeneralSettingsCard(initial)
    traffic_card = TrafficRulesCard(initial)

    tab_defs = [
        {"icon": ft.Icons.TUNE, "title_key": "k", "default_title": "General", "cards": [general_card, traffic_card]}
    ]

    view = SettingsView(
        locale_manager=mock_lm, settings_client=mock_client, tab_definitions=tab_defs, warning_text_ref=ft.Text("warn")
    )
    mock_page = MagicMock()
    mock_page.theme_mode = ft.ThemeMode.DARK
    view.page = mock_page
    general_card.page = mock_page
    traffic_card.page = mock_page

    # Simulate user changing values without saving
    traffic_card.tf_min_green_time.value = "99"
    general_card.check_theme.value = False
    mock_page.theme_mode = ft.ThemeMode.LIGHT

    # Call discard_changes
    view.discard_changes()

    # Verify everything reverted to saved settings
    assert traffic_card.tf_min_green_time.value == "10"
    assert general_card.check_theme.value is True
    assert mock_page.theme_mode == ft.ThemeMode.DARK


def test_settings_save_then_discard_reverts_to_saved(tmp_path):
    ini_file = tmp_path / "settings.ini"
    cfg = configparser.ConfigParser()
    cfg.add_section("TRAFFIC_RULES")
    cfg.set("TRAFFIC_RULES", "min_green_time", "10")
    cfg.set("TRAFFIC_RULES", "yellow_time", "3")
    with open(ini_file, "w") as f:
        cfg.write(f)

    mock_lm = MagicMock()
    mock_lm.get_string.return_value = "Mock"
    mock_client = MagicMock()
    test_handler = SettingsHandler(config_path=str(ini_file))

    initial = {"min_green_time": "10", "yellow_time": "3"}
    traffic_card = TrafficRulesCard(initial)
    tab_defs = [{"icon": ft.Icons.TUNE, "title_key": "k", "default_title": "T", "cards": [traffic_card]}]

    view = SettingsView(
        locale_manager=mock_lm,
        settings_client=mock_client,
        tab_definitions=tab_defs,
        warning_text_ref=ft.Text("w"),
        handler=test_handler,
    )
    mock_page = MagicMock()
    view.page = mock_page
    traffic_card.page = mock_page
    view.dialog_manager = MagicMock()

    # Modify and save
    traffic_card.tf_min_green_time.value = "25"
    view._execute_save()

    mock_client.save_settings.assert_called_once()

    # Modify again without saving
    traffic_card.tf_min_green_time.value = "99"

    # Discard should revert to 25 (the saved value), NOT 10
    view.discard_changes()
    assert traffic_card.tf_min_green_time.value == "25"
