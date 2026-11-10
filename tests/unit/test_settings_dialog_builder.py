# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Unit tests for SettingsDialogBuilder and dialog closing lifecycle."""

from unittest.mock import MagicMock
import configparser
import flet as ft
import pytest

from ui.builders.settings_dialog_builder import SettingsDialogBuilder
from ui.cards.traffic_rules_card import TrafficRulesCard
from ui.handlers.settings_handler import SettingsHandler
from ui.views.settings_view import SettingsView


def test_settings_dialog_builder_close_discards_unsaved_changes():
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
    assert view.has_unsaved_changes() is True

    # User clicks Close (action button)
    close_button = dialog.actions[0]
    close_button.on_click()

    # Prompt is shown; dialog stays open until decision
    assert dialog.open is True
    assert view.dialog_manager._dialog.open is True

    # User selects "Descartar"
    discard_button = view.dialog_manager._dialog.actions[1]
    discard_button.on_click(None)

    # Dialog should be closed and modifications discarded
    assert dialog.open is False
    assert view.dialog_manager._dialog.open is False
    assert traffic_card.tf_min_green_time.value == "10"


def test_settings_dialog_builder_close_save_and_close(tmp_path):
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
    mock_page.overlay = []
    view.page = mock_page
    traffic_card.page = mock_page

    dialog, open_dialog = SettingsDialogBuilder.build_settings_dialog(
        page=mock_page, locale_manager=mock_lm, security_ui=None, settings_view=view, settings_client=mock_client
    )

    open_dialog()
    traffic_card.tf_min_green_time.value = "25"
    assert view.has_unsaved_changes() is True

    # User clicks Close
    close_button = dialog.actions[0]
    close_button.on_click()
    assert dialog.open is True

    # User chooses "Salvar e Fechar" (the third action button)
    save_and_close_button = view.dialog_manager._dialog.actions[2]
    save_and_close_button.on_click(None)

    # Saved to client and dialog closed
    mock_client.save_settings.assert_called_once()
    assert dialog.open is False
    assert view.has_unsaved_changes() is False


def test_settings_dialog_builder_close_cancel():
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
    traffic_card.tf_min_green_time.value = "55"

    # User clicks Close
    close_button = dialog.actions[0]
    close_button.on_click()

    # User chooses "Cancelar" (the first action button)
    cancel_button = view.dialog_manager._dialog.actions[0]
    cancel_button.on_click(None)

    # Confirmation dialog closed, but settings dialog remains open and value preserved
    assert view.dialog_manager._dialog.open is False
    assert dialog.open is True
    assert traffic_card.tf_min_green_time.value == "55"


def test_settings_dialog_builder_close_without_changes_closes_immediately():
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
    assert view.has_unsaved_changes() is False

    # User clicks Close without modifying anything
    close_button = dialog.actions[0]
    close_button.on_click()

    # Closes immediately without prompt
    assert dialog.open is False
    assert view.dialog_manager._dialog.open is False
