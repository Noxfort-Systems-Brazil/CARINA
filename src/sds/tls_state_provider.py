# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Description:
Specialist class responsible for providing the current operational state
(colors/phases and global display state) of traffic lights.
Features a 2-Stage Visual Transition Engine that renders realistic Yellow phases
followed by All-Red clearance phases during telemetry phase jumps.
"""

import configparser
import time

from sds.tls_map_extractor import TlsMapExtractor
from utils.safety_rules import SafetyRules
from utils.settings_manager import SettingsManager


class TlsStateProvider:
    """
    Acts as the definitive source of truth for the UI dashboard.
    Converts the phase telemetry from the Formatter into realistic colored states,
    enforcing a strict physical flow: Green -> Yellow -> All-Red -> Next Green.
    """

    _current_display_phases = {}
    _transition_timers = {}

    _yellow_duration_seconds = None
    _all_red_duration_seconds = None

    @classmethod
    def get_live_states_for_junction(cls, incoming_edges: list, tl_id: str, phase_idx: int) -> dict:
        """
        Calculates the realistic traffic light state for a given set of approaching streets.
        Directly queries the current active phase without artificial transition delays,
        ensuring perfect correspondence between the UI dashboard and the controller telemetry.
        """
        lanes_state_dict = {}

        focal_groups = TlsMapExtractor.get_all_focal_groups_for_tl(tl_id)

        if not focal_groups:
            lanes_state_dict["Unknown_Group"] = "r"
            return {"lanes_state": lanes_state_dict, "display_state": "RED"}

        extracted_colors = TlsMapExtractor.get_edge_colors_for_phase(tl_id, phase_idx)

        # Map the resolved colors to the focal groups
        for fg in focal_groups:
            lanes_state_dict[fg] = extracted_colors.get(fg, "r")

        # --- GLOBAL DISPLAY STATE LOGIC ---
        all_states_str = "".join(str(v) for v in lanes_state_dict.values()).lower()
        if not all_states_str:
            all_states_str = "r"

        if any(c in all_states_str for c in ["y", "s"]):
            display_state = "YELLOW"
        elif any(c in all_states_str for c in ["g"]):
            display_state = "GREEN"
        else:
            display_state = "RED"

        return {"lanes_state": lanes_state_dict, "display_state": display_state}
