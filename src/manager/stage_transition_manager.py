# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import Any, Dict

from utils.safety_rules import SafetyRules


class StageTransitionManager:
    """
    Component specialized in managing physical stage transitions
    (Yellow, All-red, Red) based on elapsed simulation time.
    """

    def __init__(self, state_extractor, action_supervisor):
        self.state_extractor = state_extractor
        self.action_supervisor = action_supervisor
        self.yellow_time = SafetyRules.get_yellow()
        self.all_red_time = SafetyRules.get_all_red()

    def auto_advance_transitions(self, sim_time: float, current_stages: Dict[str, Any]):
        """
        Advances physical transitions automatically based on elapsed simulation time.

        Args:
            sim_time (float): Current simulation time
            current_stages (Dict): Dictionary containing current stages for each TL
        """
        for tl_id in list(current_stages.keys()):
            current_stage_idx = current_stages.get(tl_id, 0)
            green_stages = self.state_extractor.tl_green_stages.get(tl_id, [])

            # If current stage is NOT a green stage, it's a physical transition (Yellow, Red, etc)
            if green_stages and current_stage_idx not in green_stages:
                duration = sim_time - self.action_supervisor._last_stage_change_time.get(tl_id, 0)
                stage_codes = self.state_extractor.tl_stage_codes.get(tl_id, {})
                state_string = stage_codes.get(current_stage_idx, "").upper()
                total_stages = len(stage_codes)

                if total_stages == 0:
                    continue

                advanced = False
                if "Y" in state_string and duration >= self.yellow_time:
                    current_stages[tl_id] = (current_stage_idx + 1) % total_stages
                    advanced = True
                    logging.debug(
                        f"[StageTransitionManager] TL {tl_id} YELLOW->NEXT stage after {duration:.2f}s (threshold: {self.yellow_time}s)"
                    )
                elif "R" in state_string:
                    prev_stage_idx = (current_stage_idx - 1) % total_stages
                    prev_state_string = stage_codes.get(prev_stage_idx, "").upper()

                    stage_durations = getattr(self.state_extractor, "tl_stage_durations", {}).get(tl_id, {})
                    default_duration = stage_durations.get(current_stage_idx, 0.0)
                    if default_duration > 0:
                        is_clearance = ("Y" in prev_state_string) and (default_duration <= self.all_red_time)
                    else:
                        is_clearance = "Y" in prev_state_string

                    threshold = self.all_red_time if is_clearance else SafetyRules.get_red()

                    if duration >= threshold:
                        current_stages[tl_id] = (current_stage_idx + 1) % total_stages
                        advanced = True
                        logging.debug(
                            f"[StageTransitionManager] TL {tl_id} RED->NEXT stage after {duration:.2f}s (threshold: {threshold}s)"
                        )
                elif "Y" in state_string:
                    logging.debug(
                        f"[StageTransitionManager] TL {tl_id} in YELLOW stage for {duration:.2f}s (threshold: {self.yellow_time}s)"
                    )
                elif "R" in state_string:
                    logging.debug(f"[StageTransitionManager] TL {tl_id} in RED stage for {duration:.2f}s")

                if advanced:
                    # Keep the exact start time of the newly entered stage to maintain sync
                    self.action_supervisor._last_stage_change_time[tl_id] = sim_time
                    logging.info(f"[StageTransitionManager] TL {tl_id} advanced to stage {current_stages[tl_id]}")

    def update_estimated_stage(
        self, tl_id: str, current_stage_idx: int, sim_time: float, current_stages: Dict[str, Any]
    ):
        """
        Strictly initiates transition to the next logical stage (typically Yellow).

        Args:
            tl_id (str): Traffic light ID
            current_stage_idx (int): Current stage index
            sim_time (float): Current simulation time
            current_stages (Dict): Dictionary containing current stages for each TL
        """
        stage_codes = self.state_extractor.tl_stage_codes.get(tl_id, {})
        total_stages = len(stage_codes)

        if total_stages == 0:
            logging.warning(f"[StageTransitionManager] No stage codes found for TL {tl_id}")
            return

        # Instead of skipping directly to the next Green, just move to the next immediate stage (+1)
        next_stage_idx = (current_stage_idx + 1) % total_stages
        current_stages[tl_id] = next_stage_idx

        # Mark precisely when this intermediate stage was initiated by the hardware Actuator
        self.action_supervisor._last_stage_change_time[tl_id] = sim_time

        # Log the stage transition for debugging
        current_state = stage_codes.get(current_stage_idx, "UNKNOWN").upper()
        next_state = stage_codes.get(next_stage_idx, "UNKNOWN").upper()
        logging.info(
            f"[StageTransitionManager] TL {tl_id} stage transition: {current_state} -> {next_state} at time {sim_time:.2f}"
        )

    def apply_software_transitions(
        self, actions_to_apply: Dict[str, int], sim_time: float, current_stages: Dict[str, Any]
    ) -> None:
        """
        Applies software phase updates for all actions requesting a stage transition (action == 0).
        """
        for tl_id, action in actions_to_apply.items():
            if action == 0:
                current_stage_idx = current_stages.get(tl_id, 0)
                self.update_estimated_stage(tl_id, current_stage_idx, sim_time, current_stages)

