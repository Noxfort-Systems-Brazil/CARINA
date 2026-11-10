# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from src.evp.evp_service import EVPService
from ui.controllers.evp_fleet_controller import EVPFleetController


@pytest.mark.unit
def test_evp_fleet_controller_dependency_injection():
    """Validates that controller accepts EVPService dependency injection."""
    custom_service = EVPService()
    controller = EVPFleetController(evp_service=custom_service)
    assert controller.evp_service is custom_service
    assert controller.get_fleet() == []


@pytest.mark.unit
def test_evp_fleet_controller_register_and_unregister():
    """Validates manual registration and vehicle removal via EVPFleetController."""
    service = EVPService()
    controller = EVPFleetController(evp_service=service)

    # 1. Fails when registering without ID
    ok, msg = controller.register_vehicle({"vehicle_id": ""})
    assert ok is False
    assert "obrigatório" in msg.lower()

    # 2. Succeeds when registering valid vehicle
    valid_data = {
        "vehicle_id": "SAMU-10",
        "corporation": "SAMU",
        "plate": "SAM-1010",
        "ip_address": "10.8.0.50",
        "port": 8085,
        "protocol": "HTTP",
        "device_id": "IMEI-123",
        "auth_token": "token-123",
        "description": "Ambulância Teste",
    }
    ok, msg = controller.register_vehicle(valid_data)
    assert ok is True
    assert "SAMU-10" in msg

    fleet = controller.get_fleet()
    assert len(fleet) == 1
    assert fleet[0]["vehicle_id"] == "SAMU-10"

    # 3. Successful removal
    removed = controller.unregister_vehicle("SAMU-10")
    assert removed is True
    assert controller.get_fleet() == []

    # 4. Telemetry received right after removal must not re-register or reappear in get_fleet()
    from src.evp.evp_models import TelemetryData, CorporationType
    service.process_telemetry(
        TelemetryData(
            vehicle_id="SAMU-10",
            corporation=CorporationType.SAMU,
            latitude=-23.5505,
            longitude=-46.6333,
            speed_kmh=45.0,
        )
    )
    assert controller.get_fleet() == []

    # 5. Non-existent vehicle removal
    assert controller.unregister_vehicle("INEXISTENTE") is False



@pytest.mark.unit
def test_evp_fleet_controller_csv_import_export(tmp_path):
    """Validates CSV spreadsheet operations intermediated by EVPFleetController."""
    service = EVPService()
    controller = EVPFleetController(evp_service=service)

    csv_file = tmp_path / "fleet_ctrl.csv"
    csv_file.write_text(
        "vehicle_id,corporation,plate,device_id,ip_address,port,protocol,auth_token,description,is_active\n"
        "POL-99,POLICIA,POL9999,IMEI-99,10.8.0.99,8085,HTTP,sec_99,Viatura Patrulha,true\n",
        encoding="utf-8",
    )

    success, total = controller.import_csv(str(csv_file))
    assert success == 1
    assert total == 1

    fleet = controller.get_fleet()
    assert len(fleet) == 1
    assert fleet[0]["vehicle_id"] == "POL-99"

    export_file = tmp_path / "export_ctrl.csv"
    assert controller.export_csv(str(export_file)) is True
    assert export_file.exists()


@pytest.mark.unit
def test_evp_fleet_controller_reimport_previously_deleted_vehicle_via_csv(tmp_path):
    """Validates that previously deleted vehicles can be reimported via CSV and connected."""
    from src.evp.evp_models import TelemetryData, CorporationType

    service = EVPService()
    controller = EVPFleetController(evp_service=service)

    # 1. Registers initial vehicle then removes it
    controller.register_vehicle({
        "vehicle_id": "SAMU-01",
        "corporation": "SAMU",
        "plate": "BRA2E19",
    })
    controller.save_changes()
    assert len(controller.get_fleet()) == 1

    removed = controller.unregister_vehicle("SAMU-01")
    assert removed is True
    assert len(controller.get_fleet()) == 0
    assert service.fleet_manager.is_vehicle_unregistered("SAMU-01") is True

    # 2. Reimports CSV sheet containing SAMU-01
    csv_file = tmp_path / "reimport.csv"
    csv_file.write_text(
        "vehicle_id,corporation,plate,device_id,ip_address,port,protocol,auth_token,is_active\n"
        "SAMU-01,SAMU,BRA2E19,IMEI-1234,10.8.0.15,8085,HTTP,tok_samu,true\n",
        encoding="utf-8",
    )
    success, total = controller.import_csv(str(csv_file))
    assert success == 1
    assert total == 1

    # 3. Should immediately appear in staged fleet
    fleet = controller.get_fleet()
    assert len(fleet) == 1
    assert fleet[0]["vehicle_id"] == "SAMU-01"

    # 4. Saves changes to database
    controller.save_changes()
    assert service.fleet_manager.is_vehicle_unregistered("SAMU-01") is False

    # 5. Simulator telemetry should connect and show ONLINE
    service.process_telemetry(
        TelemetryData(
            vehicle_id="SAMU-01",
            corporation=CorporationType.SAMU,
            latitude=-23.5505,
            longitude=-46.6333,
            speed_kmh=60.0,
            siren_active=True,
        )
    )

    fleet = controller.get_fleet()
    assert len(fleet) == 1
    assert fleet[0]["vehicle_id"] == "SAMU-01"
    assert fleet[0]["is_online"] is True
    assert fleet[0]["status"] == "ONLINE"
    assert fleet[0]["speed_kmh"] == 60.0
