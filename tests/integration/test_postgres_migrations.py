# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

# File: tests/integration/test_postgres_migrations.py
# Author: Gabriel Moraes
# Date: September 2026

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
