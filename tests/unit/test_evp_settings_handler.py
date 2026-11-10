# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import MagicMock, patch

from src.evp.evp_models import CorporationType, RegisteredVehicle
from ui.handlers.evp_settings_handler import EVPSettingsHandler


@pytest.fixture
def mock_evp_service():
    service = MagicMock()
    service.get_registered_fleet.return_value = [
        {
            "vehicle_id": "SAMU-01",
            "corporation": "SAMU",
            "plate": "SAM1000",
            "description": "Ambulância Alpha",
            "ip_address": "10.0.0.1",
            "port": 8080,
            "protocol": "HTTP",
            "is_active": True,
        }
    ]
    service.is_vehicle_unregistered.return_value = False
    return service


@pytest.fixture
def mock_page():
    page = MagicMock()
    page.overlay = []
    page.update = MagicMock()
    return page


@pytest.fixture
def mock_card():
    card = MagicMock()
    card.update_fleet_list = MagicMock()
    card.page = MagicMock()
    return card


@pytest.mark.unit
def test_evp_settings_handler_mount_and_no_unsaved(mock_evp_service, mock_page, mock_card):
    """Verifies that the handler mounts snapshot and reports no unsaved changes."""
    handler = EVPSettingsHandler(evp_service=mock_evp_service)
    handler.mount(mock_page, mock_card)

    assert handler.has_unsaved_changes() is False
    mock_card.fleet_table.set_vehicles.assert_called_once()


@pytest.mark.unit
def test_evp_settings_handler_stage_register_and_discard(mock_evp_service, mock_page, mock_card):
    """Verifies staging registration chaining and discard restoring original snapshot."""
    handler = EVPSettingsHandler(evp_service=mock_evp_service)
    handler.mount(mock_page, mock_card)

    new_v = RegisteredVehicle(
        vehicle_id="BOMBEIRO-02",
        corporation=CorporationType.BOMBEIRO,
        plate="BOM2000",
        ip_address="10.0.0.2",
    )
    handler.on_register_vehicle(new_v)

    # Unsaved changes should be present
    assert handler.has_unsaved_changes() is True
    assert "BOMBEIRO-02" in handler._staged_fleet

    # Discard changes
    handler.discard_changes()
    assert handler.has_unsaved_changes() is False
    assert "BOMBEIRO-02" not in handler._staged_fleet
    assert "SAMU-01" in handler._staged_fleet


@pytest.mark.unit
def test_evp_settings_handler_stage_removal_and_discard(mock_evp_service, mock_page, mock_card):
    """Verifies staging removal chaining and discard restoring original snapshot."""
    handler = EVPSettingsHandler(evp_service=mock_evp_service)
    handler.mount(mock_page, mock_card)

    handler.on_remove_vehicle("SAMU-01")
    assert handler.has_unsaved_changes() is True
    assert "SAMU-01" not in handler._staged_fleet
    assert "SAMU-01" in handler._staged_removals

    handler.discard_changes()
    assert handler.has_unsaved_changes() is False
    assert "SAMU-01" in handler._staged_fleet
    assert len(handler._staged_removals) == 0


@pytest.mark.unit
def test_evp_settings_handler_save_changes_persists(mock_evp_service, mock_page, mock_card):
    """Verifies that save_changes persists added and removed vehicles in repository and service."""
    handler = EVPSettingsHandler(evp_service=mock_evp_service)
    handler.mount(mock_page, mock_card)

    new_v = RegisteredVehicle(
        vehicle_id="POLICIA-03",
        corporation=CorporationType.POLICIA,
        plate="POL3000",
        ip_address="10.0.0.3",
    )
    handler.on_register_vehicle(new_v)
    handler.on_remove_vehicle("SAMU-01")

    with patch("src.evp.evp_config_repo.EVPConfigRepository.save_vehicle_db") as mock_save, \
         patch("src.evp.evp_config_repo.EVPConfigRepository.remove_vehicle_db") as mock_remove:
        mock_save.return_value = True
        mock_remove.return_value = True

        success = handler.save_changes()
        assert success is True
        mock_save.assert_called_once()
        mock_remove.assert_called_once_with("SAMU-01", locale_manager=None)
        mock_evp_service.register_fleet_vehicle.assert_called_once()
        mock_evp_service.unregister_fleet_vehicle.assert_called_once_with("SAMU-01")

    assert handler.has_unsaved_changes() is False
