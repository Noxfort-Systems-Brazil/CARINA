# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import sqlite3
import tempfile
from unittest.mock import MagicMock

import pytest
from alembic import command
from alembic.config import Config

from src.database.db_engine import DatabaseEngine


def test_alembic_upgrade_and_downgrade_sqlite():
    """Validates complete upgrade and downgrade lifecycle on a clean SQLite database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db_path = os.path.join(tmpdir, "test_migration.db")
        os.environ["CARINA_DB_TYPE"] = "sqlite"

        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        alembic_ini_path = os.path.join(project_root, "alembic.ini")
        alembic_cfg = Config(alembic_ini_path)
        alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{test_db_path}")

        # 1. Execute upgrade to head
        command.upgrade(alembic_cfg, "head")

        conn = sqlite3.connect(test_db_path)
        cursor = conn.cursor()

        # Verify all 12 core tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {row[0] for row in cursor.fetchall()}

        expected_tables = {
            "simulation_runs",
            "episodes",
            "analysis_reports",
            "synapse_fluid_dynamics",
            "synapse_edge_phase_hourly_summary",
            "synapse_intersection_phase_hourly_summary",
            "cloud_file_vault",
            "hardware_controller_connections",
            "sas_analysis_cache",
            "mfd_analysis_cache",
            "step_decisions",
            "edge_dictionary",
            "operation_sessions",
            "evp_telemetry_records",
            "evp_registered_fleet",
            "step_decision_counters",
            "topology_dictionary",
            "alembic_version",
        }
        for table in expected_tables:
            assert table in tables, f"Expected table '{table}' not found in database."

        # Verify columns in synapse_fluid_dynamics
        cursor.execute("PRAGMA table_info(synapse_fluid_dynamics);")
        columns = {row[1] for row in cursor.fetchall()}
        assert "sample_count" in columns
        assert "edge_int_id" in columns
        assert "maturity_stage" in columns
        assert "scenario_name" in columns

        # Verify alembic_version has head revision
        cursor.execute("SELECT version_num FROM alembic_version;")
        version = cursor.fetchone()[0]
        assert version == "002"

        conn.close()

        # 2. Execute downgrade to base
        command.downgrade(alembic_cfg, "base")

        conn = sqlite3.connect(test_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        remaining_tables = {row[0] for row in cursor.fetchall() if row[0] != "alembic_version"}
        assert len(remaining_tables) == 0, f"Tables still exist after downgrade: {remaining_tables}"
        conn.close()


def test_database_engine_apply_migrations_method():
    """Tests the DatabaseEngine.apply_migrations() integration."""
    lm = MagicMock()
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db_name = os.path.join(tmpdir, "test_engine_migration.db")
        db_engine = DatabaseEngine(locale_manager=lm, db_name=test_db_name)
        assert hasattr(db_engine, "apply_migrations")
        success = db_engine.apply_migrations()
        assert success is True
