# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import os

import pytest
from alembic import command
from alembic.config import Config


@pytest.mark.integration
def test_alembic_postgres_migrations():
    """
    Validates Alembic upgrade and downgrade against a real PostgreSQL instance.
    Runs when CARINA_DB_TYPE=postgres or when PostgreSQL service is detected.
    """
    db_type = os.getenv("CARINA_DB_TYPE", "sqlite")
    if db_type != "postgres":
        pytest.skip("PostgreSQL not configured in current environment (set CARINA_DB_TYPE=postgres).")

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    alembic_ini_path = os.path.join(project_root, "alembic.ini")
    alembic_cfg = Config(alembic_ini_path)

    # 1. Upgrade to head
    command.upgrade(alembic_cfg, "head")

    # 2. Downgrade to base
    command.downgrade(alembic_cfg, "base")

    # 3. Re-upgrade to head
    command.upgrade(alembic_cfg, "head")
