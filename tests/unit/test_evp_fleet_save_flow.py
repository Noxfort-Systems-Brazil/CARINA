# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import MagicMock
import flet as ft

from src.database.db_engine import DatabaseEngine
from src.evp.evp_config_repo import EVPConfigRepository
from src.evp.evp_models import CorporationType, RegisteredVehicle
from src.evp.evp_service import EVPService
from ui.builders.settings_dialog_builder import SettingsDialogBuilder
from ui.handlers.evp_settings_handler import EVPSettingsHandler
from ui.views.settings_view import SettingsView


@pytest.mark.unit
def test_evp_save_flow_prevents_premature_discard_and_persists(tmp_path):
    """
    Tests that clicking 'Save Changes' prevents the modal flow from
    prematurely discarding the EVP fleet buffer before user confirmation,
    guaranteeing complete persistence in the database.
    """
    test_db = str(tmp_path / "test_evp_flow.db")
    engine = DatabaseEngine(locale_manager=None, db_name=test_db)

    # 1. Setup mock page and components
    page = MagicMock(spec=ft.Page)
    page.overlay = []

    locale_manager = MagicMock()
    locale_manager.get_string.side_effect = lambda key, default="", **kw: default or key

    settings_client = MagicMock()

    evp_service = EVPService()
    evp_handler = EVPSettingsHandler(
        evp_service=evp_service,
        settings_client=settings_client,
        locale_manager=locale_manager,
    )

    warning_text = ft.Text("")
    tab_definitions = [
        {"icon": ft.Icons.SETTINGS, "title_key": "tab", "default_title": "Tab", "cards": []}
    ]

    settings_view = SettingsView(
        locale_manager=locale_manager,
        settings_client=settings_client,
        tab_definitions=tab_definitions,
        warning_text_ref=warning_text,
    )
    settings_view.evp_handler = evp_handler
    settings_view.page = page

    # Override engine in EVPConfigRepository by patching save/load or using custom engine
    # In EVPSettingsHandler.save_changes:
    def custom_save():
        for v in evp_handler.buffer.staged_fleet.values():
            EVPConfigRepository.save_vehicle_db(v, locale_manager=locale_manager, engine=engine)
        evp_handler.buffer.commit_changes()
        return True

    evp_handler.save_changes = custom_save

    # 2. Constructs modal dialog
    settings_dialog, open_dialog = SettingsDialogBuilder.build_settings_dialog(
        page=page,
        locale_manager=locale_manager,
        security_ui=None,
        settings_view=settings_view,
        settings_client=settings_client,
    )

    # 3. Adds vehicle to staging buffer
    v1 = RegisteredVehicle(
        vehicle_id="SAMU-TEST",
        corporation=CorporationType.SAMU,
        plate="TEST1234",
        description="Ambulância Teste",
        device_id="IMEI-TEST",
        ip_address="10.8.0.15",
        port=8085,
        protocol="HTTP",
        is_active=True,
    )
    evp_handler.buffer.stage_vehicle(v1)
    assert "SAMU-TEST" in evp_handler.buffer.staged_fleet
    assert evp_handler.has_unsaved_changes() is True

    # 4. User clicks 'Save Changes' (_save_click)
    # Should set _is_saving = True and open confirmation dialog
    settings_view._save_click(None)
    assert getattr(settings_view, "_is_saving", False) is True

    # 5. Flet emits dismiss event on background dialog (settings_dialog)
    # Because _is_saving = True, discard MUST be ignored!
    settings_dialog.on_dismiss(None)
    settings_view.discard_changes()

    # Buffer MUST remain intact
    assert "SAMU-TEST" in evp_handler.buffer.staged_fleet

    # 6. User confirms save in modal dialog
    confirm_callback = settings_view.dialog_manager._on_confirm_callback
    assert confirm_callback is not None
    confirm_callback()

    # _is_saving should have returned to False
    assert getattr(settings_view, "_is_saving", False) is False

    # 7. Verifies that vehicle was effectively written to database
    loaded_fleet = EVPConfigRepository.load_all_vehicles_db(locale_manager=locale_manager, engine=engine)
    assert "SAMU-TEST" in loaded_fleet
    assert loaded_fleet["SAMU-TEST"].plate == "TEST1234"


@pytest.mark.unit
def test_evp_save_flow_cancel_allows_subsequent_discard(tmp_path):
    """
    Tests that canceling the confirmation dialog resets the _is_saving flag to False,
    allowing a subsequent explicit discard to work normally.
    """
    locale_manager = MagicMock()
    locale_manager.get_string.side_effect = lambda key, default="", **kw: default or key
    settings_client = MagicMock()

    evp_service = EVPService()
    evp_handler = EVPSettingsHandler(
        evp_service=evp_service,
        settings_client=settings_client,
        locale_manager=locale_manager,
    )

    settings_view = SettingsView(
        locale_manager=locale_manager,
        settings_client=settings_client,
        tab_definitions=[],
        warning_text_ref=ft.Text(""),
    )
    settings_view.evp_handler = evp_handler
    page = MagicMock(spec=ft.Page)
    page.overlay = []
    settings_view.page = page

    # Mount dialog manager
    from ui.dialogs.confirmation_dialog_manager import ConfirmationDialogManager
    settings_view.dialog_manager = ConfirmationDialogManager(page, locale_manager)

    # 1. Adds vehicle to staging
    v1 = RegisteredVehicle(
        vehicle_id="POLICIA-CANCEL",
        corporation=CorporationType.POLICIA,
        plate="POL9999",
        description="Viatura Cancelamento",
        is_active=True,
    )
    evp_handler.buffer.stage_vehicle(v1)
    assert "POLICIA-CANCEL" in evp_handler.buffer.staged_fleet

    # 2. Clicks save
    settings_view._save_click(None)
    assert settings_view._is_saving is True

    # 3. User cancels dialog
    settings_view.dialog_manager._handle_cancel()
    assert settings_view._is_saving is False

    # 4. Explicit discard should now work normally
    settings_view.discard_changes()
    assert "POLICIA-CANCEL" not in evp_handler.buffer.staged_fleet
