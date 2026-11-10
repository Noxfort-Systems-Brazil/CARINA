# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Dict, Optional

from core.dynamic_entropy_calculator import DynamicEntropyCalculator
from core.enums import Maturity
from maturity.agent_maturity import AgentMaturity
from maturity.maturity_reporter import MaturityReporter
from promotion.promotion_evaluator import PromotionEvaluator


class MaturityPromotionService:
    """
    Domain Service responsible for evaluating agent metrics against entropy safety ceilings
    and MFD network thresholds, applying promotions and emitting reports.
    """

    def __init__(
        self,
        entropy_calculator: DynamicEntropyCalculator,
        promotion_evaluator: PromotionEvaluator,
        reporter: MaturityReporter,
    ) -> None:
        self.entropy_calculator = entropy_calculator
        self.promotion_evaluator = promotion_evaluator
        self.reporter = reporter

    def check_and_promote(
        self,
        agents: Dict[str, AgentMaturity],
        agent_metrics: dict,
        child_phase_duration: int,
        teen_phase_min_duration: int,
        mfd_efficiency: float = 0.0,
        manual_max_entropy: Optional[float] = None,
        is_automatic_mode: bool = False,
    ) -> bool:
        """
        Processes episode metrics for all agents and applies promotions if criteria are met.
        Returns True if at least one agent was promoted.
        """
        promotion_happened = False
        mode_str = "AUTOMÁTICO" if is_automatic_mode else "MANUAL"

        for agent_id, metrics in agent_metrics.items():
            if agent_id not in agents:
                continue

            agent = agents[agent_id]
            agent.record_episode(metrics.get("reward", 0))

            current_phase = agent.phase
            episodes_in_phase = agent.episodes_in_phase
            agent_entropy = metrics.get("entropy", float("inf"))

            if current_phase == Maturity.CHILD:
                dynamic_child_threshold = self.entropy_calculator.calculate_threshold(
                    child_phase_duration, is_adult_transition=False
                )
                if not is_automatic_mode and manual_max_entropy is not None:
                    # Safety invariant: manual setting can only be stricter (lower), never looser
                    threshold_to_use = min(dynamic_child_threshold, float(manual_max_entropy))
                else:
                    threshold_to_use = dynamic_child_threshold

                confidence_ok = agent_entropy < threshold_to_use
                is_promoted, reason, _, required_episodes = self.promotion_evaluator.evaluate_agent(
                    agent_id=agent_id,
                    current_phase=current_phase,
                    episodes_in_phase=episodes_in_phase,
                    recent_mfd_efficiency=mfd_efficiency,
                )

                if confidence_ok and is_promoted:
                    details = self.reporter.build_promotion_details(
                        episodes_in_phase, required_episodes, agent_entropy, threshold_to_use, reason, mode_str=mode_str
                    )
                    agent.promote(Maturity.TEEN)
                    self.reporter.report_promotion(agent_id, Maturity.TEEN, details)
                    promotion_happened = True
                else:
                    rejection = self.reporter.build_rejection_details(
                        episodes_in_phase,
                        required_episodes,
                        agent_entropy,
                        threshold_to_use,
                        confidence_ok,
                        is_promoted,
                        reason,
                        mode_str=mode_str,
                    )
                    self.reporter.report_rejection(agent_id, current_phase, Maturity.TEEN, rejection)

            elif current_phase == Maturity.TEEN:
                dynamic_adult_threshold = self.entropy_calculator.calculate_threshold(
                    teen_phase_min_duration, is_adult_transition=True
                )
                if not is_automatic_mode and manual_max_entropy is not None:
                    # Safety invariant: manual setting can only be stricter (lower), never looser
                    threshold_to_use = min(dynamic_adult_threshold, float(manual_max_entropy))
                else:
                    threshold_to_use = dynamic_adult_threshold
                confidence_ok = agent_entropy < threshold_to_use
                is_promoted, reason, _, required_episodes = self.promotion_evaluator.evaluate_agent(
                    agent_id=agent_id,
                    current_phase=current_phase,
                    episodes_in_phase=episodes_in_phase,
                    recent_mfd_efficiency=mfd_efficiency,
                )

                if confidence_ok and is_promoted:
                    details = self.reporter.build_promotion_details(
                        episodes_in_phase, required_episodes, agent_entropy, threshold_to_use, reason, mode_str=mode_str
                    )
                    agent.promote(Maturity.ADULT)
                    self.reporter.report_promotion(agent_id, Maturity.ADULT, details)
                    promotion_happened = True
                else:
                    rejection = self.reporter.build_rejection_details(
                        episodes_in_phase,
                        required_episodes,
                        agent_entropy,
                        threshold_to_use,
                        confidence_ok,
                        is_promoted,
                        reason,
                        mode_str=mode_str,
                    )
                    self.reporter.report_rejection(agent_id, current_phase, Maturity.ADULT, rejection)

        return promotion_happened
