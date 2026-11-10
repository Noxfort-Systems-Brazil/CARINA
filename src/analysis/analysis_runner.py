# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Defines the AnalysisRunner, a specialist class responsible for
executing the system's analysis phase.
"""
import logging
from typing import Any, Dict, List

from core.childhood_analyzer import ChildhoodAnalyzer
from engine.episode_runner import EpisodeRunner


class AnalysisRunner:
    """
    Orchestrates the execution of analysis episodes to establish
    the baseline and traffic profiles, using the EpisodeRunner.
    """

    def __init__(self, episode_runner: EpisodeRunner, analyzer: ChildhoodAnalyzer):
        """
        Initializes the Analysis Runner.
        """
        self.episode_runner = episode_runner
        self.analyzer = analyzer
        self.locale_manager = analyzer.locale_manager
        logging.info("[ANALYSIS_RUNNER] Analysis Phase Runner created.")

    def run(self) -> tuple:
        """
        Executes complete analysis cycle and returns the results.
        """
        lm = self.locale_manager
        # The log has been generalized as mode is no longer an important distinction here.
        logging.info("[ANALYSIS_RUNNER] Starting initial analysis phase...")

        all_episode_metrics: List[Dict[str, Any]] = []

        for i in range(self.analyzer.analysis_episodes):
            logging.info(f"   L- Executing analysis episode {i+1}/{self.analyzer.analysis_episodes}...")

            # --- MAIN CHANGE HERE ---
            # The call to 'run' now no longer needs the 'mode' parameter.
            # The episode performed will be a full training episode.
            episode_metrics = self.episode_runner.run(episode_count=(i + 1))
            # --- END OF CHANGE ---

            if episode_metrics:
                all_episode_metrics.append(episode_metrics)

        # The results of these first training episodes are used to define the baseline.
        profiles, baseline = self.analyzer.run_analysis(all_episode_metrics)

        self.analyzer.save_to_cache(profiles, baseline)

        return profiles, baseline
