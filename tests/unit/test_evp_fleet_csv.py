# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from src.evp.evp_fleet_manager import EVPFleetManager
from src.evp.evp_models import CorporationType, RegisteredVehicle
from src.evp.evp_service import EVPService


@pytest.mark.unit
def test_evp_import_and_export_fleet_connection_csv(tmp_path):
    """Validates import and export of CSV spreadsheets with network parameters and authentication."""
    service = EVPService()

    csv_file = tmp_path / "frota_teste.csv"
    csv_content = (
        "vehicle_id,corporation,plate,device_id,ip_address,port,protocol,auth_token,description,is_active\n"
        "USA-01,SAMU,BRA2E19,IMEI-12345,192.168.1.50,8085,HTTP,token_123,Ambulância UTI,true\n"
        "ABS-02,BOMBEIRO,SPB1930,IMEI-67890,192.168.1.60,9000,UDP,token_456,Auto Bomba,true\n"
        "ROCAM-03,POLICIA,PMM1900,IMEI-11111,192.168.1.70,8085,HTTP,token_789,Ronda Ostensiva,false\n"
    )
    csv_file.write_text(csv_content, encoding="utf-8")

    success, total = service.import_fleet_connection_csv(str(csv_file))
    assert success == 3
    assert total == 3

    fleet = {v["vehicle_id"]: v for v in service.get_registered_fleet()}
    assert "USA-01" in fleet
    assert fleet["USA-01"]["corporation"] == "SAMU"
    assert fleet["USA-01"]["device_id"] == "IMEI-12345"
    assert fleet["USA-01"]["is_active"] is True
    assert fleet["ROCAM-03"]["is_active"] is False

    export_file = tmp_path / "export_template.csv"
    ok = service.export_fleet_csv_template(str(export_file))
    assert ok is True
    assert export_file.exists()
    assert "USA-01" in export_file.read_text(encoding="utf-8-sig")


@pytest.mark.unit
def test_evp_fleet_manager_authorization_and_crud():
    """Validates formal registration, deactivation, and authorization verification in EVPFleetManager."""
    mgr = EVPFleetManager(auto_register=False)

    veh = RegisteredVehicle(
        vehicle_id="PM_SPECIAL",
        corporation=CorporationType.POLICIA,
        plate="ABC1234",
        is_active=True,
    )
    mgr.register_vehicle(veh)
    assert mgr.is_vehicle_authorized("PM_SPECIAL") is True
    assert mgr.is_vehicle_authorized("UNKNOWN") is False

    assert mgr.unregister_vehicle("PM_SPECIAL") is True
    assert mgr.is_vehicle_authorized("PM_SPECIAL") is False
    assert mgr.unregister_vehicle("NOT_FOUND") is False
