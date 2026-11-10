# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import sqlite3
import pytest
from unittest.mock import MagicMock

from src.database.db_engine import DatabaseEngine
from src.evp.evp_config_repo import EVPConfigRepository
from src.evp.evp_models import CorporationType, RegisteredVehicle


@pytest.fixture
def test_db_engine(tmp_path):
    db_file = str(tmp_path / "test_evp_repo.db")
    engine = DatabaseEngine(locale_manager=None, db_name=db_file)
    return engine


@pytest.mark.unit
def test_evp_config_repo_save_and_load(test_db_engine):
    """Verifies vehicle saving and loading in database via static repository."""
    v1 = RegisteredVehicle(
        vehicle_id="REPO-TEST-01",
        corporation=CorporationType.SAMU,
        plate="RPO1001",
        description="Ambulância Teste Repositório",
        ip_address="192.168.10.15",
        port=8080,
        protocol="HTTP",
        is_active=True,
    )

    success = EVPConfigRepository.save_vehicle_db(v1, engine=test_db_engine)
    assert success is True

    vehicles = EVPConfigRepository.load_all_vehicles_db(engine=test_db_engine)
    assert len(vehicles) >= 1
    found = vehicles.get("REPO-TEST-01")
    assert found is not None
    assert found.plate == "RPO1001"
    assert found.corporation == CorporationType.SAMU
    assert found.ip_address == "192.168.10.15"
    assert found.port == 8080


@pytest.mark.unit
def test_evp_config_repo_remove_and_denied(test_db_engine):
    """Verifies vehicle removal and addition to denied/unauthorized list."""
    v1 = RegisteredVehicle(
        vehicle_id="REPO-REMOVE-02",
        corporation=CorporationType.BOMBEIRO,
        plate="RPO2002",
        ip_address="192.168.10.20",
    )
    EVPConfigRepository.save_vehicle_db(v1, engine=test_db_engine)

    # Remove
    removed = EVPConfigRepository.remove_vehicle_db("REPO-REMOVE-02", engine=test_db_engine)
    assert removed is True

    vehicles = EVPConfigRepository.load_all_vehicles_db(engine=test_db_engine)
    assert "REPO-REMOVE-02" not in vehicles

    denied = EVPConfigRepository.load_denied_vehicles_db(engine=test_db_engine)
    assert "REPO-REMOVE-02" in denied


@pytest.mark.unit
def test_evp_config_repo_clear_all(test_db_engine):
    """Verifies complete clearing of fleet and denied vehicles."""
    v1 = RegisteredVehicle(vehicle_id="CLR-01", corporation=CorporationType.POLICIA)
    v2 = RegisteredVehicle(vehicle_id="CLR-02", corporation=CorporationType.BOMBEIRO)
    EVPConfigRepository.save_vehicle_db(v1, engine=test_db_engine)
    EVPConfigRepository.save_vehicle_db(v2, engine=test_db_engine)

    EVPConfigRepository.clear_all_vehicles_db(engine=test_db_engine)

    vehicles = EVPConfigRepository.load_all_vehicles_db(engine=test_db_engine)
    denied = EVPConfigRepository.load_denied_vehicles_db(engine=test_db_engine)
    assert len(vehicles) == 0
    assert len(denied) == 0


@pytest.mark.unit
def test_evp_config_repo_csv_import_and_export(tmp_path, test_db_engine):
    """Verifies database-persisted CSV import and CSV template export."""
    csv_file = str(tmp_path / "fleet_import.csv")
    csv_content = (
        "vehicle_id,corporation,plate,description,ip_address,port,protocol,is_active\n"
        "CSV-IMP-01,SAMU,SAM1111,Ambulância CSV,10.0.0.1,8080,HTTP,True\n"
        "CSV-IMP-02,BOMBEIRO,BOM2222,Caminhão CSV,10.0.0.2,8080,TCP,True\n"
    )
    with open(csv_file, "w", encoding="utf-8") as f:
        f.write(csv_content)

    imported = EVPConfigRepository.import_csv_config(csv_file)
    assert len(imported) == 2
    for v in imported:
        EVPConfigRepository.save_vehicle_db(v, engine=test_db_engine)

    vehicles = EVPConfigRepository.load_all_vehicles_db(engine=test_db_engine)
    assert "CSV-IMP-01" in vehicles
    assert "CSV-IMP-02" in vehicles

    # Export
    export_file = str(tmp_path / "fleet_export.csv")
    exported = EVPConfigRepository.export_csv_template(export_file, fleet=vehicles)
    assert exported is True
    assert os.path.exists(export_file)
    with open(export_file, "r", encoding="utf-8") as f:
        exported_text = f.read()
    assert "CSV-IMP-01" in exported_text
    assert "CSV-IMP-02" in exported_text
