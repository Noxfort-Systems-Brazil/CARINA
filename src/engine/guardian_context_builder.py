# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Guardian Context Builder (Engine Layer / SOLID: SRP).
Builds safety evaluation contexts for Guardian Agent symbolic firewall audits.
"""

from typing import Any, Dict
from utils.safety_rules import SafetyRules


class GuardianContextBuilder:
    """Builds structured context dictionaries for Guardian Agent audits."""

    @staticmethod
    def build_context(
        tl_id: str,
        current_stage_idx: int,
        sim_time: float,
        state_extractor: Any,
        action_supervisor: Any,
    ) -> Dict[str, Any]:
        """Constructs temporal and geometric context for symbolic safety evaluation."""
        current_stage_duration = sim_time - action_supervisor._last_stage_change_time.get(tl_id, 0)
        state_string = state_extractor.tl_stage_codes.get(tl_id, {}).get(current_stage_idx, "G")

        prev_stage_idx = (current_stage_idx - 1) % len(state_extractor.tl_stage_codes.get(tl_id, {0: "G"}))
        prev_state_string = state_extractor.tl_stage_codes.get(tl_id, {}).get(prev_stage_idx, "").upper()

        stage_durations = getattr(state_extractor, "tl_stage_durations", {}).get(tl_id, {})
        default_duration = stage_durations.get(current_stage_idx, 0.0)

        all_red_time = SafetyRules.get_all_red()
        if default_duration > 0:
            is_clearance_red = ("Y" in prev_state_string) and (default_duration <= all_red_time)
        else:
            is_clearance_red = "Y" in prev_state_string

        return {
            "tl_id": tl_id,
            "current_stage_duration": current_stage_duration,
            "current_stage_state": state_string.upper(),
            "next_stage_has_flow": True,
            "is_clearance_red": is_clearance_red,
        }
