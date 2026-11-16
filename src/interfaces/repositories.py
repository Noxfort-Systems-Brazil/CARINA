# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Repository Ports (Clean Architecture / Hexagonal Ports & SOLID: ISP + DIP).
Segregates persistence contracts into narrow reader, writer, maintenance,
and domain-specific repository protocols.
"""

from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional, Protocol, Tuple, runtime_checkable

from src.maturity.maturity_repository_port import MaturityRepositoryPort


@runtime_checkable
class IFluidDynamicsReader(Protocol):
    """Read-only port for querying historical and aggregated traffic fluid dynamics (ISP)."""

    def query_fluid_dynamics_history(self, limit_seconds: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieves fluid dynamics samples currently stored in the database."""
        ...

    def query_fluid_dynamics_history_batches(
        self, limit_seconds: Optional[int] = None, batch_size: int = 50000
    ) -> Iterator[List[Dict[str, Any]]]:
        """Yields batches of fluid dynamics samples from the database."""
        ...

    def query_aggregated_fluid_dynamics(self, limit_seconds: Optional[int] = None) -> List[Dict[str, Any]]:
        """Executes pushdown aggregation query grouped by edge_id."""
        ...


@runtime_checkable
class IFluidDynamicsWriter(Protocol):
    """Write-only port for ingesting real-time traffic fluid dynamics samples (ISP)."""

    def insert_synapse_fluid_dynamics(self, samples: List[Dict[str, Any]]) -> None:
        """Batch-inserts a list of fluid dynamics sample dicts."""
        ...


@runtime_checkable
class IFluidDynamicsMaintenance(Protocol):
    """Maintenance port for retention, compaction, and purging of historical samples (ISP)."""

    def consolidate_and_purge_old_data(self, keep_hours: int = 48, batch_days: int = 1) -> None:
        """Consolidates raw fluid dynamics data into hourly summaries and purges raw rows."""
        ...

    def purge_old_fluid_dynamics(self, keep_minutes: int = 1440) -> None:
        """Deletes fluid dynamics samples older than keep_minutes."""
        ...


@runtime_checkable
class IFluidDynamicsRepository(IFluidDynamicsReader, IFluidDynamicsWriter, IFluidDynamicsMaintenance, Protocol):
    """Full contract for FluidDynamicsRepository combining reader, writer, maintenance, and metrics."""

    def get_fluid_dynamics_count(self) -> int: ...

    def get_fluid_dynamics_time_range(self) -> float: ...

    def get_fluid_dynamics_min_max_timestamps(
        self, limit_seconds: Optional[int] = None
    ) -> Tuple[Optional[datetime], Optional[datetime]]: ...


@runtime_checkable
class ISimulationRepository(Protocol):
    """Port for simulation runs, episodes, analysis reports, and SAS/MFD baselines."""

    def create_simulation_run(self, scenario_name: str) -> Optional[int]: ...

    def log_episode(self, run_id: int, episode_number: int, total_reward: float) -> None: ...

    def log_analysis_report(self, run_id: int, summary: str, report_content: str) -> None: ...

    def get_sas_analysis_cache(self, scenario_name: str) -> dict: ...

    def save_sas_analysis_cache(self, scenario_name: str, cache_data: dict) -> None: ...

    def get_mfd_analysis_baselines(self, scenario_name: str) -> tuple: ...

    def save_mfd_analysis_baselines(self, scenario_name: str, snapshot: dict) -> None: ...


@runtime_checkable
class IStepDecisionRepository(Protocol):
    """Port for step decision counters, operational sessions, and guardian veto analytics."""

    def increment_decision_counter_batch(self, batch_tuples: List[Tuple[int, int, int]]) -> bool: ...

    def start_session(self) -> Optional[int]: ...

    def end_session(
        self, session_id: int, status: str = "FINALIZADO_NORMAL", error_msg: Optional[str] = None
    ) -> bool: ...

    def bulk_save_topology_elements(self, elements: List[Dict[str, Any]]) -> bool: ...

    def update_topology_custom_name(self, element_type: str, raw_net_id: str, new_name: str) -> bool: ...

    def get_topology_custom_name(self, element_type: str, raw_net_id: str) -> Optional[str]: ...

    def get_all_audited_agent_ids(self) -> List[str]: ...

    def get_guardian_veto_statistics(self, agent_id: Optional[str] = None) -> Dict[str, Any]: ...


@runtime_checkable
class ICloudVaultRepository(Protocol):
    """Port for cloud file vault synchronization and restoration."""

    def sync_file_to_vault(self, filepath: str, base_dir: str) -> bool: ...

    def sync_all_files_to_vault(self, base_dir: str) -> None: ...

    def fetch_file_from_vault(self, relative_path: str) -> Optional[bytes]: ...

    def restore_file_from_vault(self, relative_path: str, target_filepath: str) -> bool: ...

    def restore_all_files_from_vault(self, base_dir: str) -> int: ...


@runtime_checkable
class IAgentCheckpointRepository(Protocol):
    """Port for persisting and restoring neural agent checkpoints on disk."""

    def get_checkpoint_dir(self, map_path: str) -> str: ...

    def save_system_state(
        self,
        map_path: str,
        agents: Dict[str, Any],
        strategist: Optional[Any],
        shared_pae: Optional[Any] = None,
        guardians: Optional[Dict[str, Any]] = None,
    ) -> None: ...

    def restore_system_state(
        self,
        map_path: str,
        agents: Dict[str, Any],
        strategist: Optional[Any],
        shared_pae: Optional[Any] = None,
        guardians: Optional[Dict[str, Any]] = None,
        device: Optional[Any] = None,
    ) -> None: ...


@runtime_checkable
class IConnectionConfigCSVStorage(Protocol):
    """Port for importing and exporting intersection connection spreadsheets (CSV)."""

    def export_csv_template(self, filepath: str, saved_ips: Dict[str, str], known_intersections: List[str]) -> bool: ...

    def import_csv_entries(self, filepath: str) -> Dict[str, Dict[str, Any]]: ...

    def import_csv_config(self, filepath: str) -> Dict[str, str]: ...


@runtime_checkable
class IConnectionConfigRepository(Protocol):
    """Port for database persistence of hardware intersection connection configs."""

    def save_connection_db(
        self,
        intersection_id: str,
        ip_address: str,
        locale_manager: Any = None,
        engine: Any = None,
        snmp_config: Optional[Dict[str, Any]] = None,
    ) -> bool: ...

    def remove_connection_db(
        self,
        intersection_id: str,
        locale_manager: Any = None,
        engine: Any = None,
    ) -> bool: ...

    def load_connection_configs_with_snmp_db(
        self,
        locale_manager: Any = None,
        engine: Any = None,
    ) -> Dict[str, Dict[str, Any]]: ...

    def load_all_snmp_configs_db(
        self,
        locale_manager: Any = None,
        engine: Any = None,
    ) -> Dict[str, Dict[str, Any]]: ...

    def load_all_connections_db(
        self,
        locale_manager: Any = None,
        engine: Any = None,
    ) -> Dict[str, str]: ...

    def clear_all_connections_db(
        self,
        locale_manager: Any = None,
        engine: Any = None,
    ) -> bool: ...


IMaturityRepository = MaturityRepositoryPort

__all__ = [
    "IFluidDynamicsReader",
    "IFluidDynamicsWriter",
    "IFluidDynamicsMaintenance",
    "IFluidDynamicsRepository",
    "ISimulationRepository",
    "IStepDecisionRepository",
    "ICloudVaultRepository",
    "IAgentCheckpointRepository",
    "IConnectionConfigCSVStorage",
    "IConnectionConfigRepository",
    "IMaturityRepository",
    "MaturityRepositoryPort",
]
