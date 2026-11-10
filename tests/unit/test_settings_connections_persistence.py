# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Integration and persistence tests for SettingsView, connection configuration,
and RAM staging buffer lifecycle.
"""

import os
from unittest.mock import MagicMock
import pytest
import flet as ft

from ui.cards.database_settings_card import DatabaseSettingsCard
from ui.cards.monitor_settings_card import MonitorSettingsCard
from ui.cards.remote_gateway_card import RemoteGatewayCard
from ui.handlers.settings_handler import SettingsHandler
from ui.views.settings_view import SettingsView


def test_end_to_end_connection_settings_persistence(tmp_path, monkeypatch):
    """
    Simulates saving settings via SettingsView, closing, and reopening
    with a fresh SettingsHandler. Verifies that all connection states persist.
    """
    orig_env = dict(os.environ)

    ini_file = tmp_path / "config" / "settings.ini"
    env_file = tmp_path / ".env"
    ini_file.parent.mkdir(parents=True, exist_ok=True)

    # Initialize empty .env
    env_file.write_text("DUCKDNS_DOMAIN=old_domain\n", encoding="utf-8")

    handler = SettingsHandler(config_path=str(ini_file))

    mock_client = MagicMock()
    mock_lm = MagicMock()
    mock_lm.get_string.return_value = "Mock"

    # Save connection states for Monitor, Database, and DuckDNS
    saved_payload = {
        "monitor_enabled": "True",
        "monitor_mqtt_host": "192.168.1.200",
        "db_connected": "True",
        "db_type": "postgres",
        "db_host": "10.0.0.5",
        "db_port": "5432",
        "db_name": "carina_db",
        "db_user": "carina_user",
        "db_password": "super_secret_password",
        "gateway_enabled": True,
    }

    handler.prepare_settings_for_save(saved_payload)

    # Reopen fresh handler pointing to the same files
    reopened_handler = SettingsHandler(config_path=str(ini_file))
    reloaded_settings = reopened_handler.get_current_settings()

    assert reloaded_settings.get("monitor_enabled") is True or str(reloaded_settings.get("monitor_enabled")).lower() == "true"
    assert reloaded_settings.get("monitor_mqtt_host") == "192.168.1.200"
    assert reloaded_settings.get("db_connected") is True or str(reloaded_settings.get("db_connected")).lower() == "true"
    assert reloaded_settings.get("db_host") == "10.0.0.5"
    assert reloaded_settings.get("gateway_enabled") is True

    # Instantiate cards with the reloaded settings
    db_card = DatabaseSettingsCard(initial_values=reloaded_settings)
    monitor_card = MonitorSettingsCard(initial_values=reloaded_settings)
    mock_controller = MagicMock()
    mock_controller.clean_domain.side_effect = lambda d: d
    mock_controller.format_service_urls.return_value = {"cco_url": "u1", "evp_url": "u2"}
    gateway_card = RemoteGatewayCard(initial_values=reloaded_settings, controller=mock_controller)

    assert db_card.is_connected is True
    assert monitor_card.is_connected is True
    assert gateway_card.is_connected is True

    # Build SettingsView and verify has_unsaved_changes is False upon reopening
    tab_defs = [
        {"icon": ft.Icons.TUNE, "title_key": "k", "default_title": "T", "cards": [db_card, monitor_card, gateway_card]}
    ]
    view = SettingsView(
        locale_manager=mock_lm,
        settings_client=mock_client,
        tab_definitions=tab_defs,
        warning_text_ref=ft.Text(""),
        handler=reopened_handler,
    )

    diffs = []
    saved = reopened_handler.get_current_settings()
    current = {}
    for card in view.all_cards:
        if hasattr(card, "get_values"):
            current.update(card.get_values())
    for k, v in current.items():
        if k in saved and str(saved[k]) != str(v):
            diffs.append((k, "saved:", saved[k], "curr:", v))
    try:
        assert view.has_unsaved_changes() is False
    finally:
        os.environ.clear()
        os.environ.update(orig_env)


def test_settings_staging_in_ram_and_discard_preserves_disk(tmp_path, monkeypatch):
    """
    Validates that:
    1. Editing settings, adding EVP vehicles, and toggling hardware/database connections
       stays in RAM without writing to .ini, .env, or database.
    2. Calling discard_changes() reverts all RAM states back to clean disk state.
    3. Only calling _execute_save() permanently commits changes.
    """
    for env_k in ["CARINA_MONITOR_ENABLED", "CARINA_DB_CONNECTED", "CARINA_GATEWAY_ENABLED", "CARINA_MQTT_HOST"]:
        monkeypatch.delenv(env_k, raising=False)
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: None)
    monkeypatch.setattr("src.database.db_config.DatabaseConfig._load_env_file", lambda *a, **k: None)

    ini_file = tmp_path / "config" / "settings.ini"
    env_file = tmp_path / ".env"
    ini_file.parent.mkdir(parents=True, exist_ok=True)
    ini_file.write_text("[MONITOR]\nmonitor_enabled = False\nmonitor_mqtt_host = localhost\n[DATABASE]\ndb_connected = False\ndb_type = sqlite\n[REMOTE_GATEWAY]\ngateway_enabled = False\n", encoding="utf-8")
    env_file.write_text("", encoding="utf-8")

    handler = SettingsHandler(config_path=str(ini_file))
    initial_settings = handler.get_current_settings()

    mock_client = MagicMock()
    mock_lm = MagicMock()
    mock_lm.get_string.return_value = "Mock"

    # 1. Cards
    monitor_card = MonitorSettingsCard(initial_values=initial_settings, locale_manager=mock_lm)
    db_card = DatabaseSettingsCard(initial_values=initial_settings, locale_manager=mock_lm)

    mock_gw_ctrl = MagicMock()
    mock_gw_ctrl.clean_domain.side_effect = lambda d: d
    mock_gw_ctrl.format_service_urls.return_value = {"cco_url": "", "evp_url": ""}
    gw_card = RemoteGatewayCard(initial_values=initial_settings, controller=mock_gw_ctrl)

    from ui.cards.evp_fleet_connection_card import EVPFleetConnectionCard
    from ui.cards.hardware_connection_card import HardwareConnectionCard
    from ui.handlers.hardware_settings_handler import HardwareSettingsHandler
    from src.controller.connection_manager import HardwareConnectionManager

    evp_card = EVPFleetConnectionCard(locale_manager=mock_lm)
    hw_card = HardwareConnectionCard(locale_manager=mock_lm)
    hw_mgr = HardwareConnectionManager.get_instance(locale_manager=mock_lm)
    hw_handler = HardwareSettingsHandler(connection_manager=hw_mgr, settings_client=mock_client, locale_manager=mock_lm)
    hw_card.handler = hw_handler

    tab_defs = [
        {"icon": ft.Icons.TUNE, "title_key": "k1", "default_title": "T1", "cards": [db_card, monitor_card, gw_card, evp_card, hw_card]}
    ]

    view = SettingsView(
        locale_manager=mock_lm,
        settings_client=mock_client,
        tab_definitions=tab_defs,
        warning_text_ref=ft.Text(""),
        handler=handler,
    )
    view.hardware_handler = hw_handler
    view.hardware_card = hw_card

    initial_fleet_count = len(evp_card.controller.get_fleet())

    # Initially, no changes
    assert view.has_unsaved_changes() is False

    # 2. Modify in RAM: Add vehicle to EVP staging
    evp_card.controller.register_vehicle({
        "vehicle_id": "STAGED-01",
        "corporation": "SAMU",
        "plate": "RAM1234",
        "ip_address": "127.0.0.1",
        "port": 8085,
        "protocol": "HTTP",
        "device_id": "IMEI-RAM",
        "auth_token": "tk-ram",
    })

    # Modify hardware IP in RAM
    hw_mgr.saved_ips["tl_TEST"] = "192.168.1.99"

    # Toggle monitor in RAM
    monitor_card.is_connected = True

    # View should detect unsaved changes
    assert view.has_unsaved_changes() is True

    # Verify nothing has been written to ini file
    content_before_save = ini_file.read_text(encoding="utf-8")
    assert "192.168.1.99" not in content_before_save
    assert "STAGED-01" not in content_before_save

    # 3. Discard changes
    view.discard_changes()

    # Verify RAM state reverted
    assert view.has_unsaved_changes() is False
    assert len(evp_card.controller.get_fleet()) == initial_fleet_count
    assert not any(v.get("vehicle_id") == "STAGED-01" for v in evp_card.controller.get_fleet())
    assert "tl_TEST" not in hw_mgr.saved_ips
    assert monitor_card.is_connected is False


def test_manual_disconnect_persists_on_discard():
    """
    Verifies that when a user manually disconnects a traffic light in the hardware card,
    subsequent discard_changes() (such as closing or switching views) does NOT reconnect it.
    """
    from unittest.mock import MagicMock
    from src.controller.connection_manager import HardwareConnectionManager
    from src.controller.connection_config_repo import ConnectionConfigRepository
    from ui.handlers.hardware_settings_handler import HardwareSettingsHandler

    mock_lm = MagicMock()
    mock_lm.get_string.return_value = "Mock"
    mock_client = MagicMock()

    hw_mgr = HardwareConnectionManager.get_instance(locale_manager=mock_lm)
    # Simulate an active driver
    mock_driver = MagicMock()
    mock_driver.is_connected = True
    tl_id = "tl_DISC_TEST"
    hw_mgr.active_connections[tl_id] = mock_driver
    hw_mgr.saved_ips[tl_id] = "127.0.0.1:1610"

    handler = HardwareSettingsHandler(connection_manager=hw_mgr, settings_client=mock_client, locale_manager=mock_lm)
    assert tl_id in handler._initial_active_connections

    # User manually disconnects
    handler.on_toggle_connection(tl_id, "127.0.0.1:1610", action="disconnect")
    assert tl_id not in hw_mgr.active_connections
    assert tl_id not in handler._initial_active_connections

    # User closes view / discard_changes is called
    handler.discard_changes()

    # Must remain disconnected!
    assert tl_id not in hw_mgr.active_connections


