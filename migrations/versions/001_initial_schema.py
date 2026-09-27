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

# File: migrations/versions/001_initial_schema.py
# Author: Gabriel Moraes
# Date: September 2026

"""initial CARINA schema baseline

Revision ID: 001
Revises: None
Create Date: 2026-09-26

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. simulation_runs
    op.create_table(
        "simulation_runs",
        sa.Column("run_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("start_time", sa.TIMESTAMP(), nullable=False),
        sa.Column("scenario_name", sa.Text(), nullable=True),
    )

    # 2. episodes
    op.create_table(
        "episodes",
        sa.Column("episode_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("simulation_runs.run_id"), nullable=False),
        sa.Column("episode_number", sa.Integer(), nullable=False),
        sa.Column("total_reward", sa.Float(), nullable=True),
        sa.Column("end_time", sa.TIMESTAMP(), nullable=True),
    )

    # 3. analysis_reports
    op.create_table(
        "analysis_reports",
        sa.Column("report_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("simulation_runs.run_id"), nullable=False),
        sa.Column("timestamp", sa.TIMESTAMP(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("report_content", sa.Text(), nullable=True),
    )

    # 4. synapse_fluid_dynamics
    op.create_table(
        "synapse_fluid_dynamics",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("collected_at", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False),
        sa.Column("scenario_name", sa.Text(), server_default="default", nullable=False),
        sa.Column("intersection_id", sa.Text(), nullable=True),
        sa.Column("edge_id", sa.Text(), nullable=False),
        sa.Column("density", sa.Float(), nullable=False),
        sa.Column("mean_speed", sa.Float(), nullable=False),
        sa.Column("min_speed", sa.Float(), nullable=True),
        sa.Column("queue_length", sa.Integer(), nullable=False),
        sa.Column("max_queue", sa.Integer(), nullable=True),
        sa.Column("occupancy", sa.Float(), nullable=False),
        sa.Column("edge_length", sa.Float(), nullable=True),
        sa.Column("num_lanes", sa.Integer(), nullable=True),
        sa.Column("speed_limit", sa.Float(), nullable=True),
        sa.Column("maturity_stage", sa.Text(), server_default="CHILD", nullable=False),
        sa.Column("sample_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("edge_int_id", sa.Integer(), nullable=True),
    )
    op.create_index("idx_sfd_collected_at", "synapse_fluid_dynamics", ["collected_at"])
    op.create_index("idx_sfd_edge_id", "synapse_fluid_dynamics", ["edge_id"])
    op.create_index("idx_sfd_maturity_stage", "synapse_fluid_dynamics", ["maturity_stage"])
    op.create_index(
        "idx_sfd_scen_stage_time", "synapse_fluid_dynamics", ["scenario_name", "maturity_stage", "collected_at"]
    )

    # 5. synapse_edge_phase_hourly_summary
    op.create_table(
        "synapse_edge_phase_hourly_summary",
        sa.Column("edge_id", sa.Text(), nullable=False),
        sa.Column("maturity_stage", sa.Text(), nullable=False),
        sa.Column("summary_hour", sa.TIMESTAMP(), nullable=False),
        sa.Column("scenario_name", sa.Text(), server_default="default", nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column("avg_speed", sa.Float(), nullable=False),
        sa.Column("min_speed", sa.Float(), nullable=False),
        sa.Column("avg_density", sa.Float(), nullable=False),
        sa.Column("avg_queue", sa.Float(), nullable=False),
        sa.Column("max_queue", sa.Float(), nullable=False),
        sa.Column("total_production", sa.Float(), nullable=False),
        sa.Column("avg_occupancy", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("edge_id", "maturity_stage", "summary_hour"),
    )

    # 6. synapse_intersection_phase_hourly_summary
    op.create_table(
        "synapse_intersection_phase_hourly_summary",
        sa.Column("intersection_id", sa.Text(), nullable=False),
        sa.Column("maturity_stage", sa.Text(), nullable=False),
        sa.Column("summary_hour", sa.TIMESTAMP(), nullable=False),
        sa.Column("scenario_name", sa.Text(), server_default="default", nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column("avg_speed", sa.Float(), nullable=False),
        sa.Column("min_speed", sa.Float(), nullable=False),
        sa.Column("avg_queue", sa.Float(), nullable=False),
        sa.Column("max_queue", sa.Float(), nullable=False),
        sa.Column("total_production", sa.Float(), nullable=False),
        sa.Column("total_delay", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("intersection_id", "maturity_stage", "summary_hour"),
    )

    # 7. cloud_file_vault
    op.create_table(
        "cloud_file_vault",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("relative_path", sa.Text(), nullable=False, unique=True),
        sa.Column("file_content", sa.LargeBinary(), nullable=True),
        sa.Column("last_updated", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False),
    )

    # 8. hardware_controller_connections
    op.create_table(
        "hardware_controller_connections",
        sa.Column("intersection_id", sa.Text(), primary_key=True),
        sa.Column("ip_address", sa.Text(), nullable=False),
        sa.Column("auto_connect", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("last_connected", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=True),
    )

    # 9. sas_analysis_cache
    op.create_table(
        "sas_analysis_cache",
        sa.Column("scenario_name", sa.String(length=255), primary_key=True),
        sa.Column("metrics_cache", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=True),
    )

    # 10. mfd_analysis_cache
    op.create_table(
        "mfd_analysis_cache",
        sa.Column("scenario_name", sa.String(length=255), nullable=False),
        sa.Column("cache_type", sa.String(length=50), nullable=False),
        sa.Column("metrics_cache", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("scenario_name", "cache_type"),
    )

    # 11. step_decisions
    op.create_table(
        "step_decisions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("simulation_time", sa.Float(), nullable=False),
        sa.Column("step_number", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.String(length=64), nullable=False),
        sa.Column("maturity_stage", sa.SmallInteger(), server_default="2", nullable=False),
        sa.Column("suggested_action", sa.SmallInteger(), server_default="0", nullable=False),
        sa.Column("final_decision", sa.SmallInteger(), server_default="0", nullable=False),
        sa.Column("veto_reason_code", sa.SmallInteger(), server_default="0", nullable=False),
        sa.Column("step_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("total_step_time_ms", sa.Float(), nullable=True),
        sa.Column("guardian_time_ms", sa.Float(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=True),
    )
    op.create_index("idx_sd_agent_time", "step_decisions", ["agent_id", "created_at"])
    op.create_index("idx_sd_final_decision", "step_decisions", ["final_decision", "veto_reason_code"])

    # 12. edge_dictionary
    op.create_table(
        "edge_dictionary",
        sa.Column("edge_int_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("edge_str_id", sa.String(length=255), nullable=False, unique=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=True),
    )
    op.create_index("idx_edge_dict_str", "edge_dictionary", ["edge_str_id"])


def downgrade() -> None:
    op.drop_table("edge_dictionary")
    op.drop_table("step_decisions")
    op.drop_table("mfd_analysis_cache")
    op.drop_table("sas_analysis_cache")
    op.drop_table("hardware_controller_connections")
    op.drop_table("cloud_file_vault")
    op.drop_table("synapse_intersection_phase_hourly_summary")
    op.drop_table("synapse_edge_phase_hourly_summary")
    op.drop_table("synapse_fluid_dynamics")
    op.drop_table("analysis_reports")
    op.drop_table("episodes")
    op.drop_table("simulation_runs")
