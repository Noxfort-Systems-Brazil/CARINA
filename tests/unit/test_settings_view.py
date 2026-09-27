# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
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

# File: tests/unit/test_settings_view.py
# Author: Gabriel Moraes
# Date: 2026-06-24

from unittest.mock import MagicMock

import flet as ft
import pytest


def test_settings_view_file_picker_registration():
    """
    Verifies that the logo file picker is successfully registered to the page overlay
    on mounting SettingsView, and that subsequent individual card did_mount calls
    do not register duplicates.
    """
    from ui.cards.report_formatting_card import ReportFormattingCard
    from ui.views.settings_view import SettingsView

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


def test_settings_view_discard_changes_reverts_values_and_theme():
    from ui.cards.general_settings_card import GeneralSettingsCard
    from ui.cards.traffic_rules_card import TrafficRulesCard
    from ui.views.settings_view import SettingsView

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


def test_settings_dialog_builder_close_discards_unsaved_changes():
    from ui.builders.settings_dialog_builder import SettingsDialogBuilder
    from ui.cards.traffic_rules_card import TrafficRulesCard
    from ui.views.settings_view import SettingsView

    mock_lm = MagicMock()
    mock_lm.get_string.return_value = "Mock"
    mock_client = MagicMock()

    initial = {"min_green_time": "10", "yellow_time": "3"}
    traffic_card = TrafficRulesCard(initial)
    tab_defs = [{"icon": ft.Icons.TUNE, "title_key": "k", "default_title": "T", "cards": [traffic_card]}]

    view = SettingsView(
        locale_manager=mock_lm, settings_client=mock_client, tab_definitions=tab_defs, warning_text_ref=ft.Text("w")
    )
    mock_page = MagicMock()
    mock_page.overlay = []
    view.page = mock_page
    traffic_card.page = mock_page

    dialog, open_dialog = SettingsDialogBuilder.build_settings_dialog(
        page=mock_page, locale_manager=mock_lm, security_ui=None, settings_view=view, settings_client=mock_client
    )

    open_dialog()
    assert dialog.open is True

    # User modifies field without clicking Save Changes
    traffic_card.tf_min_green_time.value = "55"

    # User clicks Close (action button)
    close_button = dialog.actions[0]
    close_button.on_click()

    # Dialog should be closed and modifications discarded
    assert dialog.open is False
    assert traffic_card.tf_min_green_time.value == "10"


def test_settings_save_then_discard_reverts_to_saved():
    from ui.cards.traffic_rules_card import TrafficRulesCard
    from ui.views.settings_view import SettingsView

    mock_lm = MagicMock()
    mock_lm.get_string.return_value = "Mock"
    mock_client = MagicMock()

    initial = {"min_green_time": "10", "yellow_time": "3"}
    traffic_card = TrafficRulesCard(initial)
    tab_defs = [{"icon": ft.Icons.TUNE, "title_key": "k", "default_title": "T", "cards": [traffic_card]}]

    view = SettingsView(
        locale_manager=mock_lm, settings_client=mock_client, tab_definitions=tab_defs, warning_text_ref=ft.Text("w")
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
