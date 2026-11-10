# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Consolidate missing runtime tables into Alembic schema

Revision ID: 002
Revises: 001
Create Date: 2026-10-10

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # 1. operation_sessions
    if "operation_sessions" not in existing_tables:
        op.create_table(
            "operation_sessions",
            sa.Column("session_id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("start_time", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=True),
            sa.Column("end_time", sa.TIMESTAMP(), nullable=True),
            sa.Column("status", sa.String(length=50), server_default="EM_OPERACAO", nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
        )

    # 2. evp_telemetry_records
    if "evp_telemetry_records" not in existing_tables:
        op.create_table(
            "evp_telemetry_records",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("vehicle_id", sa.String(length=64), nullable=False),
            sa.Column("corporation", sa.String(length=32), nullable=False),
            sa.Column("latitude", sa.Float(), nullable=False),
            sa.Column("longitude", sa.Float(), nullable=False),
            sa.Column("speed_kmh", sa.Float(), nullable=False),
            sa.Column("heading_deg", sa.Float(), nullable=False),
            sa.Column("siren_active", sa.Boolean(), nullable=False),
            sa.Column("evp_triggered", sa.Boolean(), server_default=sa.text("0"), nullable=False),
            sa.Column("intersection_id", sa.String(length=64), nullable=True),
            sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=True),
        )
        op.create_index("idx_evp_veh_time", "evp_telemetry_records", ["vehicle_id", "created_at"])
    else:
        existing_indexes = {idx["name"] for idx in inspector.get_indexes("evp_telemetry_records")}
        if "idx_evp_veh_time" not in existing_indexes:
            op.create_index("idx_evp_veh_time", "evp_telemetry_records", ["vehicle_id", "created_at"])

    # 3. evp_registered_fleet
    if "evp_registered_fleet" not in existing_tables:
        op.create_table(
            "evp_registered_fleet",
            sa.Column("vehicle_id", sa.String(length=64), primary_key=True),
            sa.Column("corporation", sa.String(length=32), nullable=False),
            sa.Column("plate", sa.String(length=16), nullable=True),
            sa.Column("description", sa.String(length=128), nullable=True),
            sa.Column("device_id", sa.String(length=64), nullable=True),
            sa.Column("ip_address", sa.String(length=45), nullable=True),
            sa.Column("port", sa.Integer(), server_default="8085", nullable=True),
            sa.Column("protocol", sa.String(length=16), server_default="HTTP", nullable=True),
            sa.Column("auth_token", sa.String(length=128), nullable=True),
            sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=True),
            sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=True),
        )

    # 4. step_decision_counters
    if "step_decision_counters" not in existing_tables:
        op.create_table(
            "step_decision_counters",
            sa.Column("agent_id", sa.BigInteger(), nullable=False),
            sa.Column("decision_code", sa.Integer(), nullable=False),
            sa.Column("count", sa.BigInteger(), server_default="0", nullable=False),
            sa.PrimaryKeyConstraint("agent_id", "decision_code"),
        )

    # 5. topology_dictionary
    if "topology_dictionary" not in existing_tables:
        op.create_table(
            "topology_dictionary",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("element_type", sa.String(length=20), nullable=False),
            sa.Column("raw_net_id", sa.String(length=255), unique=True, nullable=False),
            sa.Column("numeric_id", sa.BigInteger(), nullable=False),
            sa.Column("custom_name", sa.String(length=255), nullable=False),
            sa.Column("from_node", sa.String(length=100), nullable=True),
            sa.Column("to_node", sa.String(length=100), nullable=True),
            sa.Column("is_bidirectional_pair", sa.Boolean(), server_default=sa.text("0"), nullable=True),
        )
        op.create_index("idx_topodict_raw", "topology_dictionary", ["raw_net_id"])
    else:
        existing_indexes = {idx["name"] for idx in inspector.get_indexes("topology_dictionary")}
        if "idx_topodict_raw" not in existing_indexes:
            op.create_index("idx_topodict_raw", "topology_dictionary", ["raw_net_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "topology_dictionary" in existing_tables:
        op.drop_table("topology_dictionary")
    if "step_decision_counters" in existing_tables:
        op.drop_table("step_decision_counters")
    if "evp_registered_fleet" in existing_tables:
        op.drop_table("evp_registered_fleet")
    if "evp_telemetry_records" in existing_tables:
        op.drop_table("evp_telemetry_records")
    if "operation_sessions" in existing_tables:
        op.drop_table("operation_sessions")
