# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
GuardianSymbolicAuditor: Enforces symbolic safety firewall rules for traffic light actions.
Decomposes safety invariant validation from GuardianAgent to respect SRP and Clean Architecture.
"""

from typing import Any, Dict, Tuple


class GuardianSymbolicAuditor:
    """
    Evaluates actions against instantaneous safety invariants:
    - Minimum yellow time enforcement
    - Minimum green time enforcement
    - Ghost green (empty road) suppression
    - Clearance / all-red and red violation prevention
    """

    ACTION_KEEP_STAGE: int = 0
    ACTION_CHANGE_STAGE: int = 1

    def __init__(
        self,
        green_time: float,
        yellow_time: float,
        all_red_time: float,
        red_time: float,
        locale_manager: Any,
    ):
        self.green_time = green_time
        self.yellow_time = yellow_time
        self.all_red_time = all_red_time
        self.red_time = red_time
        self.locale_manager = locale_manager

    def audit(self, context: Dict[str, Any]) -> Tuple[int, str]:
        """
        Executes the instantaneous safety firewall rules.
        Returns: Tuple of (Action, Reason String). Action 0 = Veto. Action 1 = Allow.
        """
        current_stage_duration = context.get("current_stage_duration", 0.0)
        current_stage_state = context.get("current_stage_state", "G").upper()
        next_stage_has_flow = context.get("next_stage_has_flow", True)

        has_y = "Y" in current_stage_state
        has_g = "G" in current_stage_state

        if has_y:
            # Rule: Yellow Time Violation
            if current_stage_duration < self.yellow_time:
                return self.ACTION_KEEP_STAGE, self.locale_manager.get_string(
                    "guardian_agent.reasons.min_yellow", default="Minimum Yellow limits"
                )
        elif has_g:
            # Rule: Minimum Green Time Violation
            if current_stage_duration < self.green_time:
                return self.ACTION_KEEP_STAGE, self.locale_manager.get_string(
                    "guardian_agent.reasons.min_green", default="Minimum Green limits"
                )
            # Rule 2: No Flow / Empty Road (Ghost Green)
            if not next_stage_has_flow:
                return self.ACTION_KEEP_STAGE, self.locale_manager.get_string(
                    "guardian_agent.reasons.ghost_green", default="Ghost Green constraint"
                )
        else:
            # If it has neither Y nor G, it's a Red stage
            is_clearance_red = context.get("is_clearance_red", True)
            threshold = self.all_red_time if is_clearance_red else self.red_time

            # Rule: Red Time Violation
            if current_stage_duration < threshold:
                reason = (
                    self.locale_manager.get_string(
                        "guardian_agent.reasons.min_all_red", default="Minimum All Red limits"
                    )
                    if is_clearance_red
                    else self.locale_manager.get_string("guardian_agent.reasons.min_red", default="Minimum Red limits")
                )
                return self.ACTION_KEEP_STAGE, reason

        return self.ACTION_CHANGE_STAGE, self.locale_manager.get_string(
            "guardian_agent.reasons.symbolic_passed", default="Symbolic audit passed"
        )
