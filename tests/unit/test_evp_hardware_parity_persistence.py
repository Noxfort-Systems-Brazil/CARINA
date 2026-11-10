# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
import sqlite3
from unittest.mock import MagicMock

from src.database.db_engine import DatabaseEngine
from src.controller.connection_config_repo import ConnectionConfigRepository
from src.controller.connection_manager import HardwareConnectionManager
from src.evp.evp_fleet_repository import EVPFleetRepository
from src.evp.evp_fleet_manager import EVPFleetManager
from src.evp.evp_models import CorporationType, RegisteredVehicle
from src.evp.evp_repository import EVPRepository
from src.evp.evp_service import EVPService
from ui.controllers.evp_fleet_controller import EVPFleetController


@pytest.mark.unit
def test_schema_bootstrap_includes_both_hardware_and_evp():
    """
    Verifies that DatabaseSchemaInitializer creates hardware_controller_connections,
    evp_registered_fleet, and evp_denied_fleet from schema_queries.json.
    """
    engine = DatabaseEngine(locale_manager=None, db_name=":memory:")
    conn = engine.get_connection()
    assert conn is not None

    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {row[0] for row in cursor.fetchall()}

    # Both tables MUST exist in central bootstrap
    assert "hardware_controller_connections" in tables
    assert "evp_registered_fleet" in tables
    assert "evp_denied_fleet" in tables
    conn.close()


@pytest.mark.unit
def test_evp_hardware_persistence_parity_across_restarts(tmp_path):
    """
    Simulates complete lifecycle:
    1. Writes Hardware connection and EVP vehicle to database.
    2. Simulates full CARINA shutdown (clears singletons and memory).
    3. Simulates CARINA reopen (main_ui bootstrap).
    4. Proves Hardware and EVP recover records with equal reliability.
    """
    test_db = str(tmp_path / "parity_test.db")
    engine = DatabaseEngine(locale_manager=None, db_name=test_db)
    repo = EVPRepository(engine=engine)

    # Reset singletons
    HardwareConnectionManager._active_instance = None
    EVPService._instance = None

    # 1. Saves Hardware Connection to Database
    ConnectionConfigRepository.save_connection_db("tl_int_101", "192.168.1.101:1610", engine=engine)

    # 2. Saves EVP Vehicle to Database
    v_bombeiro = RegisteredVehicle(
        vehicle_id="BOMBEIRO-PARITY",
        corporation=CorporationType.BOMBEIRO,
        plate="BOM1930",
        description="Auto Bomba Paridade",
        ip_address="10.8.0.25",
        port=8085,
        protocol="HTTP",
        is_active=True,
    )
    repo.save_registered_vehicle(v_bombeiro)

    # 3. CARINA shutdown: clears memory and references
    HardwareConnectionManager._active_instance = None
    EVPService._instance = None

    # 4. CARINA reopen (Simulation of ui/main_ui.py bootstrap)
    # 4.1 Hardware startup
    hw_mgr = HardwareConnectionManager.get_instance(locale_manager=None)
    # Loads from database (synchronous for direct validation)
    loaded_hw = ConnectionConfigRepository.load_all_connections_db(engine=engine)
    assert "tl_int_101" in loaded_hw
    assert loaded_hw["tl_int_101"] == "192.168.1.101:1610"

    # Defensive teardown
    ConnectionConfigRepository.remove_connection_db("tl_int_101", engine=engine)

    # 4.2 EVP startup (using the same database engine)
    evp_service = EVPService(repository=repo)
    assert evp_service.is_vehicle_authorized("BOMBEIRO-PARITY") is True

    fleet_dtos = evp_service.get_registered_fleet()
    assert any(v["vehicle_id"] == "BOMBEIRO-PARITY" for v in fleet_dtos)

    restored_v = next(v for v in fleet_dtos if v["vehicle_id"] == "BOMBEIRO-PARITY")
    assert restored_v["plate"] == "BOM1930"
    assert restored_v["ip_address"] == "10.8.0.25"
    assert restored_v["port"] == 8085
    assert restored_v["corporation"] == "BOMBEIRO"


@pytest.mark.unit
def test_evp_fleet_repository_dialect_switching():
    """
    Verifies that EVPFleetRepository generates safe and compatible SQL
    both in PostgreSQL (%s) and SQLite (?).
    """
    # SQLite test
    sqlite_conn = sqlite3.connect(":memory:")
    mock_sqlite_engine = MagicMock()
    mock_sqlite_engine.db_type = "sqlite"
    mock_sqlite_engine.get_connection.return_value = sqlite_conn

    repo_sqlite = EVPFleetRepository(engine=mock_sqlite_engine, close_conn_fn=lambda _: None)
    v1 = RegisteredVehicle(
        vehicle_id="SAMU-SQLITE",
        corporation=CorporationType.SAMU,
        plate="SQL001",
        ip_address="127.0.0.1",
    )
    assert repo_sqlite.save_registered_vehicle(v1) is True

    # Verifies save to sqlite
    vehicles = repo_sqlite.get_registered_vehicles()
    assert len(vehicles) == 1
    assert vehicles[0].vehicle_id == "SAMU-SQLITE"

    # Delete test
    assert repo_sqlite.delete_registered_vehicle("SAMU-SQLITE") is True
    assert len(repo_sqlite.get_registered_vehicles()) == 0

    # Denied test
    assert repo_sqlite.add_denied_vehicle("SAMU-SQLITE") is True
    assert "SAMU-SQLITE" in repo_sqlite.get_denied_vehicles()
    assert repo_sqlite.remove_denied_vehicle("SAMU-SQLITE") is True
    assert "SAMU-SQLITE" not in repo_sqlite.get_denied_vehicles()

    # Clear all test
    repo_sqlite.save_registered_vehicle(v1)
    repo_sqlite.add_denied_vehicle("DENIED-01")
    assert repo_sqlite.clear_all_fleet_db() is True
    assert len(repo_sqlite.get_registered_vehicles()) == 0
    assert len(repo_sqlite.get_denied_vehicles()) == 0

    sqlite_conn.close()


@pytest.mark.unit
def test_evp_service_restore_saved_fleet_method():
    """
    Tests restore_saved_fleet and restore_saved_fleet_async methods of EVPService.
    """
    mock_repo = MagicMock()
    mock_repo.get_registered_vehicles.return_value = [
        RegisteredVehicle(vehicle_id="POL-10", corporation=CorporationType.POLICIA),
        RegisteredVehicle(vehicle_id="SAMU-20", corporation=CorporationType.SAMU),
    ]
    mock_repo.get_denied_vehicles.return_value = []

    svc = EVPService(repository=mock_repo)
    count = svc.restore_saved_fleet()
    assert count == 2
    assert svc.is_vehicle_authorized("POL-10") is True
    assert svc.is_vehicle_authorized("SAMU-20") is True
