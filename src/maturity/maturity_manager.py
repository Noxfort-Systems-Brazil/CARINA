# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import TYPE_CHECKING, Any, Dict, Mapping, Optional

from core.dynamic_entropy_calculator import DynamicEntropyCalculator
from core.enums import Maturity
from maturity.agent_maturity import AgentMaturity
from maturity.maturity_config import MaturityConfig
from maturity.maturity_promotion_service import MaturityPromotionService
from maturity.maturity_reporter import MaturityReporter
from maturity.maturity_repository_port import MaturityRepositoryPort
from maturity.maturity_state_serializer import MaturityStateSerializer
from promotion.promotion_evaluator import PromotionEvaluator

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend


class MaturityManager:
    """
    Application Service and Facade orchestrating traffic light agent maturity evaluations,
    delegating state serialization, configuration, and promotion logic to cohesive domain components.
    """

    def __init__(
        self,
        settings: Any,
        locale_manager: "LocaleManagerBackend",
        baseline: Optional[dict] = None,
        reporter: Optional[MaturityReporter] = None,
        population_manager: Any = None,
        repository: Optional[MaturityRepositoryPort] = None,
        entropy_calculator: Optional[DynamicEntropyCalculator] = None,
        promotion_evaluator: Optional[PromotionEvaluator] = None,
    ):
        self.locale_manager = locale_manager
        self.config = MaturityConfig.from_settings(settings, baseline)

        if repository is None:
            from repositories.maturity_state_repository import MaturityStateRepository

            self.repository: MaturityRepositoryPort = MaturityStateRepository()
        else:
            self.repository = repository

        self.reporter = reporter or MaturityReporter(locale_manager)
        raw_n = getattr(population_manager, "n_actions", 2) if population_manager is not None else 2
        n_actions = raw_n if isinstance(raw_n, int) and raw_n >= 2 else 2
        self.entropy_calculator = entropy_calculator or DynamicEntropyCalculator(
            n_actions=n_actions,
            e_max=self.config.child_promotion_max_entropy,
            e_ideal=0.1,
        )
        self.promotion_evaluator = promotion_evaluator or PromotionEvaluator(settings)
        self.promotion_service = MaturityPromotionService(
            self.entropy_calculator, self.promotion_evaluator, self.reporter
        )

        self._agents: Dict[str, AgentMaturity] = {}
        self.is_calibrated = True

        logging.info(self.locale_manager.get_string("maturity_manager.init.manager_created"))
        logging.info(
            self.locale_manager.get_string(
                "maturity_manager.init.performance_target", target=f"{self.config.baseline_target:.2f}"
            )
        )

    @property
    def baseline_performance(self) -> float:
        return self.config.baseline_performance

    @property
    def baseline_target(self) -> float:
        return self.config.baseline_target

    @property
    def performance_margin(self) -> float:
        return self.config.performance_margin

    @property
    def child_phase_duration(self) -> int:
        return self.config.child_phase_duration

    @property
    def teen_phase_min_duration(self) -> int:
        return self.config.teen_phase_min_duration

    @property
    def _rewards_window_size(self) -> int:
        return self.config.rewards_window_size

    @property
    def agent_maturity(self) -> Dict[str, Maturity]:
        """Returns a read-only dictionary snapshot mapping agent_id to its current Maturity phase."""
        return self.get_maturity_map()

    def get_maturity_map(self) -> Dict[str, Maturity]:
        """Returns a dictionary mapping agent_id to its current Maturity phase."""
        return {aid: agent.phase for aid, agent in self._agents.items()}

    def get_agent_phase(self, agent_id: str, default: Maturity = Maturity.CHILD) -> Maturity:
        """Returns the current Maturity phase for the given agent_id."""
        agent = self._agents.get(agent_id)
        return agent.phase if agent is not None else default

    def set_agent_phase(self, agent_id: str, new_phase: Maturity) -> None:
        """Explicitly sets the Maturity phase for an agent (e.g., during checkpoint restoration)."""
        agent = self.get_or_create_agent(agent_id)
        if isinstance(new_phase, Maturity):
            agent.phase = new_phase
        elif isinstance(new_phase, str) and new_phase in Maturity.__members__:
            agent.phase = Maturity[new_phase]
        else:
            raise ValueError(f"Invalid maturity value: {new_phase}")

    def get_agent(self, agent_id: str) -> Optional[AgentMaturity]:
        return self._agents.get(agent_id)

    def get_or_create_agent(self, agent_id: str) -> AgentMaturity:
        if agent_id not in self._agents:
            self._agents[agent_id] = AgentMaturity(
                agent_id=agent_id,
                phase=Maturity.CHILD,
                episodes_in_phase=0,
                reward_window_size=self._rewards_window_size,
            )
        return self._agents[agent_id]

    def get_state(self) -> dict:
        return MaturityStateSerializer.get_state(self._agents)

    def save_state(self, filepath: str) -> bool:
        return MaturityStateSerializer.save_state(self.repository, filepath, self._agents, self.locale_manager)

    def load_state(self, filepath: str) -> None:
        restored = MaturityStateSerializer.load_state(
            self.repository, filepath, self._rewards_window_size, self.locale_manager
        )
        if restored:
            self._agents.clear()
            self._agents.update(restored)
            self.register_agents(list(self._agents.keys()))

    def register_agents(self, agent_ids: list):
        new_registered = 0
        for aid in agent_ids:
            if aid not in self._agents:
                self.get_or_create_agent(aid)
                new_registered += 1
        if new_registered > 0 and self.locale_manager:
            phase_name = self.locale_manager.get_string("maturity_manager.phase_child")
            logging.info(
                self.locale_manager.get_string(
                    "maturity_manager.register.agents_registered", count=new_registered, phase=phase_name.upper()
                )
            )

    def update_calibration_thresholds(self, teen_threshold: float, adult_threshold: float):
        logging.info(
            self.locale_manager.get_string(
                "maturity_manager.calibration.thresholds_updated",
                default="[MATURITY] Note: Static calibration is disabled in favor of dynamic time-based entropy.",
            )
        )

    def set_phase_durations(self, child_episodes: int, teen_episodes: int) -> None:
        self.config.set_phase_durations(child_episodes, teen_episodes)
        if hasattr(self, "promotion_evaluator") and self.promotion_evaluator:
            self.promotion_evaluator.set_phase_durations(
                self.config.child_phase_duration, self.config.teen_phase_min_duration
            )
        logging.info(
            f"[MaturityManager] Phase durations updated: CHILD={self.config.child_phase_duration} eps, TEEN={self.config.teen_phase_min_duration} eps"
        )

    def set_performance_margin(self, margin_percent: float) -> None:
        self.config.set_performance_margin(margin_percent)
        if hasattr(self, "promotion_evaluator") and hasattr(self.promotion_evaluator, "set_performance_margin"):
            self.promotion_evaluator.set_performance_margin(float(margin_percent))
        logging.info(
            f"[MaturityManager] Performance graduation margin updated: {float(margin_percent):.2f}% (target: {self.config.baseline_target:.2f})"
        )

    @property
    def child_promotion_max_entropy(self) -> Optional[float]:
        return self.config.child_promotion_max_entropy

    @child_promotion_max_entropy.setter
    def child_promotion_max_entropy(self, value: Optional[float]) -> None:
        self.config.child_promotion_max_entropy = float(value) if value is not None else None

    @property
    def is_automatic_mode(self) -> bool:
        return self.config.is_automatic_mode

    def check_and_promote_agents(self, agent_metrics: dict, mfd_efficiency: float = 0.0) -> bool:
        return self.promotion_service.check_and_promote(
            agents=self._agents,
            agent_metrics=agent_metrics,
            child_phase_duration=self.config.child_phase_duration,
            teen_phase_min_duration=self.config.teen_phase_min_duration,
            mfd_efficiency=mfd_efficiency,
            manual_max_entropy=self.config.child_promotion_max_entropy,
            is_automatic_mode=self.config.is_automatic_mode,
        )


def resolve_agent_phase(maturity_manager: Any, agent_id: str, default: Maturity = Maturity.CHILD) -> Maturity:
    """
    O(1) phase resolution compatible with real `MaturityManager` instances
    and test doubles/mocks (`MagicMock`, `SimpleNamespace`) that populate `agent_maturity`.
    """
    if maturity_manager is None:
        return default

    # Test doubles frequently assign a plain mapping on the instance attribute `agent_maturity`.
    instance_dict = getattr(maturity_manager, "__dict__", None)
    if isinstance(instance_dict, dict) and "agent_maturity" in instance_dict:
        direct_map = instance_dict["agent_maturity"]
        if isinstance(direct_map, Mapping):
            return direct_map.get(agent_id, default)

    # Real MaturityManager stores `_agents: Dict[str, AgentMaturity]` for O(1) lookup.
    if isinstance(getattr(maturity_manager, "_agents", None), dict):
        return maturity_manager.get_agent_phase(agent_id, default)

    # Explicit custom getter (e.g. SimpleNamespace with get_agent_phase callable)
    getter = getattr(maturity_manager, "get_agent_phase", None)
    if callable(getter) and not hasattr(maturity_manager, "assert_called"):
        try:
            return getter(agent_id, default)
        except TypeError:
            return getter(agent_id)

    mat_map = getattr(maturity_manager, "agent_maturity", None)
    if isinstance(mat_map, Mapping):
        return mat_map.get(agent_id, default)

    return default


def resolve_maturity_map(maturity_manager: Any) -> Mapping[str, Maturity]:
    """Resolves a single snapshot mapping once per cycle without repeated property allocations."""
    if maturity_manager is None:
        return {}
    getter = getattr(maturity_manager, "get_maturity_map", None)
    if callable(getter) and isinstance(getattr(maturity_manager, "_agents", None), dict):
        return getter()
    mat_map = getattr(maturity_manager, "agent_maturity", None)
    return mat_map if isinstance(mat_map, Mapping) else {}
