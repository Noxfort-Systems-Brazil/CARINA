# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from src.evp.evp_fleet_manager import EVPFleetManager
from src.evp.evp_models import CorporationType, RegisteredVehicle
from src.evp.evp_service import EVPService
from src.evp.evp_repository import EVPRepository
from ui.controllers.evp_fleet_controller import EVPFleetController


@pytest.mark.unit
def test_evp_fleet_persistence_save_and_restore():
    """
    Validates that registering a vehicle persists it to database,
    and instantiating a new EVPFleetManager (simulating CARINA restart),
    recovers the vehicle with all attributes intact.
    """
    repo = EVPRepository()

    # 1. Instantiates first manager and registers
    manager_1 = EVPFleetManager(auto_register=False, repository=repo)
    v1 = RegisteredVehicle(
        vehicle_id="SAMU-99",
        corporation=CorporationType.SAMU,
        plate="ABC1D23",
        description="Ambulância Avançada",
        device_id="IMEI-998877",
        ip_address="10.8.0.77",
        port=8085,
        protocol="HTTP",
        auth_token="secret_token_99",
        is_active=True,
    )
    manager_1.register_vehicle(v1)

    assert manager_1.is_vehicle_authorized("SAMU-99") is True

    # 2. Simulates CARINA shutdown and restart (new manager)
    manager_2 = EVPFleetManager(auto_register=False, repository=repo)

    # 3. Verifies that SAMU-99 was restored from database
    restored = manager_2.get_vehicle("SAMU-99")
    assert restored is not None
    assert restored.vehicle_id == "SAMU-99"
    assert restored.corporation == CorporationType.SAMU
    assert restored.plate == "ABC1D23"
    assert restored.ip_address == "10.8.0.77"
    assert restored.port == 8085
    assert restored.protocol == "HTTP"
    assert restored.device_id == "IMEI-998877"
    assert restored.auth_token == "secret_token_99"
    assert restored.description == "Ambulância Avançada"
    assert restored.is_active is True

    # 4. Removes vehicle and verifies deletion persisted
    assert manager_2.unregister_vehicle("SAMU-99") is True

    # 5. New manager after deletion must not find vehicle and must keep it unauthorized
    manager_3 = EVPFleetManager(auto_register=False, repository=repo)
    assert manager_3.get_vehicle("SAMU-99") is None
    assert manager_3.is_vehicle_authorized("SAMU-99") is False
    assert manager_3.is_vehicle_unregistered("SAMU-99") is True


@pytest.mark.unit
def test_evp_fleet_csv_import_persistence(tmp_path):
    """
    Validates that CSV sheet import persists all vehicles to database
    and they are recovered when recreating service/controller.
    """
    csv_file = tmp_path / "frota_persist.csv"
    csv_file.write_text(
        "vehicle_id,corporation,plate,device_id,ip_address,port,protocol,auth_token,description,is_active\n"
        "BOMBEIRO-01,BOMBEIRO,SPB1001,IMEI-B1,192.168.1.10,8085,HTTP,tk_b1,Auto Bomba 01,true\n"
        "POLICIA-02,POLICIA,PMM2002,IMEI-P2,192.168.1.20,9000,UDP,tk_p2,Viatura Tática,true\n",
        encoding="utf-8",
    )

    # 1. Imports via controller (should remain in RAM / staging)
    service_1 = EVPService()
    ctrl_1 = EVPFleetController(evp_service=service_1)
    success, total = ctrl_1.import_csv(str(csv_file))
    assert success == 2
    assert total == 2
    assert ctrl_1.has_unsaved_changes() is True

    # 2. Before saving, another database service must not see vehicles
    service_uncommitted = EVPService()
    ctrl_uncommitted = EVPFleetController(evp_service=service_uncommitted)
    assert len(ctrl_uncommitted.get_fleet()) == 0

    # 3. Saves changes to database
    ctrl_1.save_changes()
    assert ctrl_1.has_unsaved_changes() is False

    # 4. Simulates CARINA closing and opening a new controller
    service_2 = EVPService()
    ctrl_2 = EVPFleetController(evp_service=service_2)

    fleet = ctrl_2.get_fleet()
    fleet_dict = {v["vehicle_id"]: v for v in fleet}

    assert "BOMBEIRO-01" in fleet_dict
    assert "POLICIA-02" in fleet_dict

    bombeiro = fleet_dict["BOMBEIRO-01"]
    assert bombeiro["plate"] == "SPB1001"
    assert bombeiro["ip_address"] == "192.168.1.10"
    assert bombeiro["port"] == 8085
    assert bombeiro["protocol"] == "HTTP"
    assert bombeiro["device_id"] == "IMEI-B1"
    assert bombeiro["auth_token"] == "tk_b1"
    assert bombeiro["description"] == "Auto Bomba 01"


@pytest.mark.unit
def test_evp_fleet_controller_ui_dtos_contain_network_fields():
    """
    Validates that build_vehicle_dtos exposes network parameters in UI
    even when vehicle is offline (newly started).
    """
    service = EVPService()
    controller = EVPFleetController(evp_service=service)

    data = {
        "vehicle_id": "RESGATE-55",
        "corporation": "SAMU",
        "plate": "RSG5555",
        "ip_address": "10.0.0.55",
        "port": 8090,
        "protocol": "HTTP",
        "device_id": "IMEI-55",
        "auth_token": "token-55",
        "description": "UTI Móvel",
    }
    ok, _ = controller.register_vehicle(data)
    assert ok is True

    fleet = controller.get_fleet()
    assert len(fleet) == 1
    dto = fleet[0]
    assert dto["vehicle_id"] == "RESGATE-55"
    assert dto["ip_address"] == "10.0.0.55"
    assert dto["port"] == 8090
    assert dto["protocol"] == "HTTP"
    assert dto["device_id"] == "IMEI-55"
    assert dto["auth_token"] == "token-55"
    assert dto["plate"] == "RSG5555"
    assert dto["description"] == "UTI Móvel"
    assert dto["status"] == "OFFLINE"


@pytest.mark.unit
def test_evp_deleted_vehicle_does_not_return_on_discard_or_telemetry():
    """
    Validates that deleting a vehicle immediately de-authorizes and removes it,
    preventing it from returning on close/discard and rejecting subsequent telemetry.
    """
    from src.evp.evp_models import TelemetryData, CorporationType

    service = EVPService()
    controller = EVPFleetController(evp_service=service)

    # 1. Registers initial vehicle
    ok, _ = controller.register_vehicle({
        "vehicle_id": "PERM-DEL-01",
        "corporation": "SAMU",
        "plate": "DEL0001",
    })
    assert ok is True
    assert any(v["vehicle_id"] == "PERM-DEL-01" for v in controller.get_fleet())

    # 2. Deletes vehicle (immediate action)
    removed = controller.unregister_vehicle("PERM-DEL-01")
    assert removed is True
    assert not any(v["vehicle_id"] == "PERM-DEL-01" for v in controller.get_fleet())

    # 3. Discard changes is triggered (like closing modal)
    controller.discard_changes()

    # Vehicle MUST remain deleted!
    assert not any(v["vehicle_id"] == "PERM-DEL-01" for v in controller.get_fleet())

    # 4. Simulator telemetry attempts to revive vehicle
    service.process_telemetry(
        TelemetryData(
            vehicle_id="PERM-DEL-01",
            corporation=CorporationType.SAMU,
            latitude=-23.55,
            longitude=-46.63,
            speed_kmh=60.0,
        )
    )

    # Vehicle MUST remain rejected and absent from fleet
    assert not any(v["vehicle_id"] == "PERM-DEL-01" for v in controller.get_fleet())
    assert service.fleet_manager.is_vehicle_unregistered("PERM-DEL-01") is True


@pytest.mark.unit
def test_evp_card_vehicle_dialog_save_persists_across_modal_close():
    """
    Validates that registering vehicle via EVPVehicleDialog modal in EVPFleetConnectionCard
    persists immediately, survives discard_changes (closing settings)
    and is recognized by EVPService for ONLINE telemetry.
    """
    from ui.cards.evp_fleet_connection_card import EVPFleetConnectionCard

    service = EVPService()
    controller = EVPFleetController(evp_service=service)
    card = EVPFleetConnectionCard(controller=controller)

    # 1. User saves vehicle in dialog
    card._on_vehicle_dialog_save({
        "vehicle_id": "SAMU-MODAL-01",
        "corporation": "SAMU",
        "plate": "SAM1001",
    })

    # Must be in fleet
    assert any(v["vehicle_id"] == "SAMU-MODAL-01" for v in controller.get_fleet())

    # 2. User closes settings without clicking general Save -> triggers discard_changes
    card.discard_changes()

    # Vehicle MUST remain saved!
    assert any(v["vehicle_id"] == "SAMU-MODAL-01" for v in controller.get_fleet())

    # 3. Simulator telemetry is received -> status becomes ONLINE
    from src.evp.evp_models import TelemetryData, CorporationType

    service.process_telemetry(
        TelemetryData(
            vehicle_id="SAMU-MODAL-01",
            corporation=CorporationType.SAMU,
            latitude=-23.5505,
            longitude=-46.6333,
            speed_kmh=50.0,
        )
    )

    fleet = controller.get_fleet()
    v_item = next(v for v in fleet if v["vehicle_id"] == "SAMU-MODAL-01")
    assert v_item["is_online"] is True
    assert v_item["status"] == "ONLINE"


