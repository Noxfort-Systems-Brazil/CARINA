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

    def load_topology(self, map_path: str) -> None:
        ...

    def get_observation_space_size(self, tl_id: str) -> int:
        ...


@runtime_checkable
class IRewardComputer(Protocol):
    """Contract for computing intersection reinforcement learning rewards."""

    def compute_reward(self, tl_id: str, raw_traffic_data: Dict[str, Any], action: int) -> Tuple[float, float, float]:
        ...


@runtime_checkable
class IActionAuthorizer(Protocol):
    """Contract for authorizing or gating agent actions according to maturity stage."""

    def authorize_action(
        self,
        tl_id: str,
        proposed_action: int,
        maturity_stage: Any,
        current_hour: Optional[int] = None,
    ) -> Tuple[int, bool]:
        ...


@runtime_checkable
class IActionSupervisor(Protocol):
    """Contract for supervising hardware clearance intervals and safety vetoes."""

    def supervise_action(self, tl_id: str, proposed_action: int, raw_state: Dict[str, Any]) -> Tuple[int, int]:
        ...


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
    ) -> FleetDecisions:
        ...


@runtime_checkable
class IStepProcessor(Protocol):
    """Contract for orchestrating a single real-time traffic control step."""

    def process_step(self, raw_traffic_data: Dict[str, Any]) -> Dict[str, Any]:
        ...


__all__ = [
    "IStateExtractor",
    "IRewardComputer",
    "IActionAuthorizer",
    "IActionSupervisor",
    "IAgentEvaluator",
    "IStepProcessor",
]
