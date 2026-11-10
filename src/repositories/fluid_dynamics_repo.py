# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from repositories.fluid_dynamics_maintenance import FluidDynamicsMaintenance
from repositories.fluid_dynamics_metrics import FluidDynamicsMetrics
from repositories.fluid_dynamics_query_provider import FluidDynamicsQueryProvider
from repositories.fluid_dynamics_reader import FluidDynamicsReader
from repositories.fluid_dynamics_writer import FluidDynamicsWriter

if TYPE_CHECKING:
    from database.db_engine import DatabaseEngine
    from utils.locale_manager_backend import LocaleManagerBackend


class FluidDynamicsRepository:
    """
    Facade and Orchestrator repository for managing synapse fluid dynamics samples.
    Delegates query management, writing, reading, maintenance, and metrics to specialized sub-components.
    """

    SAMPLE_COLUMNS = [
        "edge_id",
        "density",
        "mean_speed",
        "queue_length",
        "occupancy",
        "edge_length",
        "num_lanes",
        "speed_limit",
        "collected_at",
    ]
    AGGREGATED_COLUMNS = [
        "edge_id",
        "volume_sum",
        "volume_cnt",
        "delay_sum",
        "delay_cnt",
        "avg_queue",
        "max_queue",
        "edge_length",
        "num_lanes",
        "speed_limit",
        "total_samples",
    ]

    def __init__(self, engine: "DatabaseEngine", locale_manager: "LocaleManagerBackend"):
        self.engine = engine
        self.locale_manager = locale_manager

        # Initialize modular sub-components
        self.query_provider = FluidDynamicsQueryProvider(engine)
        self.writer = FluidDynamicsWriter(engine, self.query_provider)
        self.reader = FluidDynamicsReader(engine, self.query_provider, self.SAMPLE_COLUMNS, self.AGGREGATED_COLUMNS)
        self.maintenance = FluidDynamicsMaintenance(engine, self.query_provider)
        self.metrics = FluidDynamicsMetrics(engine, self.query_provider)

    # --- Orchestrated Public API Methods ---
    def insert_synapse_fluid_dynamics(self, samples: List[Dict]):
        """Batch-inserts a list of fluid dynamics sample dicts into synapse_fluid_dynamics."""
        self.writer.insert_synapse_fluid_dynamics(samples)

    def consolidate_and_purge_old_data(self, keep_hours: int = 48, batch_days: int = 1):
        """Consolidates raw fluid dynamics data older than keep_hours into hourly summary tables and purges raw rows."""
        self.maintenance.consolidate_and_purge_old_data(keep_hours=keep_hours, batch_days=batch_days)

    def query_fluid_dynamics_history(self, limit_seconds: int = None) -> List[Dict]:
        """Retrieves fluid dynamics samples currently stored in the database."""
        return self.reader.query_fluid_dynamics_history(limit_seconds=limit_seconds)

    def query_fluid_dynamics_history_batches(self, limit_seconds: int = None, batch_size: int = 50000):
        """Yields batches of fluid dynamics samples from the database."""
        yield from self.reader.query_fluid_dynamics_history_batches(limit_seconds=limit_seconds, batch_size=batch_size)

    def query_aggregated_fluid_dynamics(self, limit_seconds: int = None) -> List[Dict]:
        """Executes a Pushdown Aggregation Query directly on PostgreSQL/SQLite via GROUP BY edge_id."""
        return self.reader.query_aggregated_fluid_dynamics(limit_seconds=limit_seconds)

    def purge_old_fluid_dynamics(self, keep_minutes: int = 1440):
        """Deletes fluid dynamics samples older than `keep_minutes` minutes."""
        self.maintenance.purge_old_fluid_dynamics(keep_minutes=keep_minutes)

    def get_fluid_dynamics_count(self) -> int:
        """Returns the total number of fluid dynamics samples in the database."""
        return self.metrics.get_fluid_dynamics_count()

    def get_fluid_dynamics_time_range(self) -> float:
        """Calculates the difference in seconds between the oldest and newest sample across tables."""
        return self.metrics.get_fluid_dynamics_time_range()

    def get_fluid_dynamics_min_max_timestamps(
        self, limit_seconds: Optional[int] = None
    ) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Queries the MIN and MAX timestamps across synapse_fluid_dynamics and hourly summary tables."""
        return self.metrics.get_fluid_dynamics_min_max_timestamps(limit_seconds=limit_seconds)
