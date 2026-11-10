# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Component responsible for generating episode reports, such as the School Bulletin,
and managing episode-level tracking.
"""

from collections import Counter
from typing import Any, Dict

from core.enums import Maturity
from core.system_reporter import SystemReporter


class EpisodeReporter:
    """
    Component specialized in logging detailed reports at the end of each training episode.
    """

    def __init__(self, locale_manager: Any, maturity_manager: Any):
        self.lm = locale_manager
        self.maturity_manager = maturity_manager

    def report_episode_bulletin(
        self, agents: Dict[str, Any], episode_counter: int, episode_total_reward: float
    ) -> None:
        """
        Logs the detailed 'School Bulletin' at the end of each episode.

        Legacy format:
        ────────────────────────────────────────────────────────────
        END OF EPISODE {N} | SCHOOL BULLETIN
          - Episode Performance: Total Reward = {R}
          - Class Status: {A} Adults | {T} Teens | {C} Children
          - Confidence Calibration Status: Ongoing
        ────────────────────────────────────────────────────────────
        """
        maturity_counts = Counter()
        for tl_id in agents:
            phase = self.maturity_manager.agent_maturity.get(tl_id, Maturity.CHILD)
            maturity_counts[phase] += 1

        calibration_status = (
            self.lm.get_string("reporter.calib_status_done")
            if self.maturity_manager.is_calibrated
            else self.lm.get_string("reporter.calib_status_ongoing")
        )

        SystemReporter.report_school_bulletin(
            lm=self.lm,
            episode_count=episode_counter,
            total_reward=episode_total_reward,
            maturity_counts=maturity_counts,
            calibration_status=calibration_status,
        )
