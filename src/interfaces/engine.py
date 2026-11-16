# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
AI Engine Layer Protocols (SOLID: ISP & DIP).
Defines narrow contracts for the reinforcement learning inference and training pipeline.
"""

from typing import Any, Dict, Optional, Protocol, Tuple, runtime_checkable

from src.domain.value_objects import FleetDecisions


@runtime_checkable
class IStateExtractor(Protocol):
    """Contract for extracting intersection observation vectors and structural topology."""

    def load_topology(self, map_path: str) -> None: ...

    def get_observation_space_size(self, tl_id: str) -> int: ...


@runtime_checkable
class IRewardComputer(Protocol):
    """Contract for computing intersection reinforcement learning rewards."""

    def compute_reward(
        self, tl_id: str, raw_traffic_data: Dict[str, Any], action: int
    ) -> Tuple[float, float, float]: ...


@runtime_checkable
class IActionAuthorizer(Protocol):
    """Contract for authorizing or gating agent actions according to maturity stage."""

    def authorize_action(
        self,
        tl_id: str,
        proposed_action: int,
        maturity_stage: Any,
        current_hour: Optional[int] = None,
    ) -> Tuple[int, bool]: ...


@runtime_checkable
class IActionSupervisor(Protocol):
    """Contract for supervising hardware actions, holds, overrides, and transition timestamps."""

    def apply_actions(
        self,
        actions: Dict[str, int],
        current_sim_time: float = 0.0,
        current_stages: Optional[Dict[str, Any]] = None,
    ) -> None: ...

    def send_stage_hold(
        self,
        tl_id: str,
        stage_idx: int,
        stage_codes: Optional[Dict[int, str]] = None,
    ) -> None: ...

    def record_stage_change(self, tl_id: str, sim_time: float) -> None: ...

    def get_last_stage_change_time(self, tl_id: str, default: float = 0.0) -> float: ...

    def cleanup_intersection(self, tl_id: str) -> None: ...

    def reset(self) -> None: ...


@runtime_checkable
class IAgentEvaluator(Protocol):
    """Contract for evaluating the fleet of local and guardian agents during a step."""

    def evaluate_fleet(
        self,
        agents: Dict[str, Any],
        raw_traffic_data: Dict[str, Any],
        global_context: Any,
        step_counter: int,
        is_training: bool,
        shared_pae: Any = None,
        step_timer: Any = None,
    ) -> FleetDecisions: ...


@runtime_checkable
class IStepProcessor(Protocol):
    """Contract for orchestrating a single real-time traffic control step."""

    def process_step(self, raw_traffic_data: Dict[str, Any]) -> Dict[str, Any]: ...


@runtime_checkable
class IHardwareTelemetrySynchronizer(Protocol):
    """Contract for closed-loop hardware telemetry ingestion, proxy sync, and stage decoding."""

    def sync(
        self,
        traffic_data: Dict[str, Any],
        agents: Dict[str, Any],
        sim_time: float,
        current_stages: Dict[str, Any],
    ) -> Dict[str, Dict[str, Any]]: ...


@runtime_checkable
class IStrategicCoordinator(Protocol):
    """Contract for periodic ST-GATv2 strategic coordination and online value/forecasting updates."""

    def set_strategist(self, strategist: Optional[Any]) -> None: ...

    def reset(self) -> None: ...

    def update_and_distribute(
        self,
        traffic_data: Dict[str, Any],
        agents: Dict[str, Any],
        sim_time: float,
        current_stages: Dict[str, Any],
        fleet_mean_reward: float,
    ) -> None: ...


@runtime_checkable
class IPhysicalActionMasker(Protocol):
    """Contract for building physical clearance and min/max green action masks for agents."""

    def compute_mask(
        self,
        tl_id: str,
        agent: Any,
        current_stage_idx: int,
        sim_time: float,
    ) -> Optional[Any]: ...


@runtime_checkable
class IBatchedPAEEncoder(Protocol):
    """Contract for batched shared Predictive Autoencoder latent extraction across agents."""

    def encode_fleet(
        self,
        agents: Dict[str, Any],
        precomputed_states: Dict[str, Any],
    ) -> Dict[str, Any]: ...


__all__ = [
    "IStateExtractor",
    "IRewardComputer",
    "IActionAuthorizer",
    "IActionSupervisor",
    "IAgentEvaluator",
    "IStepProcessor",
    "IHardwareTelemetrySynchronizer",
    "IStrategicCoordinator",
    "IPhysicalActionMasker",
    "IBatchedPAEEncoder",
]
