# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import math
from typing import Any, Tuple

logger = logging.getLogger(__name__)


class MaturityPacingCalculator:
    """
    Calculates dynamic minimum duration (steps and episodes) for CHILD and TEEN maturity
    phases based on the loaded road network topology and training hyperparameters.
    """

    @staticmethod
    def calculate_pacing(net: Any, tls_list: Any, settings: Any = None) -> Tuple[int, int, int, int]:
        """
        Calculates required minimum steps and episodes for CHILD and TEEN phases.

        Args:
            net: SUMO network object (e.g. sumolib.net.Net) or None.
            tls_list: Collection/list of traffic lights in the network.
            settings: Configuration object or dict.

        Returns:
            Tuple containing (child_episodes, teen_episodes, child_steps, teen_steps).
        """

        def get_int(section: str, key: str, fallback: int) -> int:
            if settings is None:
                return fallback
            if hasattr(settings, "getint"):
                try:
                    return settings.getint(section, key, fallback=fallback)
                except Exception:
                    return fallback
            elif isinstance(settings, dict):
                val = settings.get(key)
                try:
                    return int(val) if val is not None else fallback
                except Exception:
                    return fallback
            return fallback

        telemetry_delta_ms = float(get_int("AI_TRAINING", "telemetry_delta_ms", 250))
        from src.utils.episode_step_calculator import EpisodeStepCalculator

        pacing_result = EpisodeStepCalculator.calculate(net, telemetry_delta_ms=telemetry_delta_ms)
        computed_episode_steps = pacing_result.episode_steps
        min_1_week_episodes = pacing_result.child_episodes_1_week

        # User-configured episodes (if any)
        configured_child_ep = get_int("MATURITY", "child_phase_episodes", min_1_week_episodes)
        configured_teen_ep = get_int("MATURITY", "teen_phase_min_episodes", min_1_week_episodes)

        # Inviolable Safety Floor: duration can be made stricter by user, but NEVER less than 1 week
        child_episodes = max(min_1_week_episodes, configured_child_ep)
        teen_episodes = max(min_1_week_episodes, configured_teen_ep)

        child_steps = child_episodes * computed_episode_steps
        teen_steps = teen_episodes * computed_episode_steps

        logger.info(
            f"[MaturityPacingCalculator] Dynamic pacing applied: EpisodeSteps={computed_episode_steps}, "
            f"CHILD={child_episodes} eps ({child_steps} steps, >= 1 week), "
            f"TEEN={teen_episodes} eps ({teen_steps} steps, >= 1 week)"
        )

        return child_episodes, teen_episodes, child_steps, teen_steps

    @staticmethod
    def apply_if_enabled(maturity_manager: Any, net: Any, tls_list: Any, settings: Any) -> bool:
        """
        If automatic phase calculation is enabled in settings, calculates and injects
        the durations directly into the maturity_manager and its promotion evaluator.

        Returns:
            True if automatic pacing was calculated and applied; False otherwise.
        """
        is_enabled = True
        if settings is not None:
            if hasattr(settings, "getboolean"):
                try:
                    is_enabled = settings.getboolean("MATURITY", "auto_pacing_enabled", fallback=True)
                except Exception:
                    is_enabled = True
            elif isinstance(settings, dict):
                val = settings.get("auto_pacing_enabled", True)
                is_enabled = str(val).lower() in ("true", "1", "yes")

        if not is_enabled:
            return False

        child_ep, teen_ep, child_steps, _ = MaturityPacingCalculator.calculate_pacing(
            net, tls_list, settings
        )
        computed_episode_steps = child_steps // child_ep if child_ep else 1000
        if settings is not None:
            if hasattr(settings, "set") and hasattr(settings, "has_section"):
                if not settings.has_section("MATURITY"):
                    settings.add_section("MATURITY")
                settings.set("MATURITY", "child_phase_episodes", str(child_ep))
                settings.set("MATURITY", "teen_phase_min_episodes", str(teen_ep))
                if not settings.has_section("AI_TRAINING"):
                    settings.add_section("AI_TRAINING")
                settings.set("AI_TRAINING", "episode_max_steps", str(computed_episode_steps))
            elif isinstance(settings, dict):
                settings["child_phase_episodes"] = str(child_ep)
                settings["teen_phase_min_episodes"] = str(teen_ep)
                settings["episode_max_steps"] = str(computed_episode_steps)

        if hasattr(maturity_manager, "set_phase_durations"):
            maturity_manager.set_phase_durations(child_ep, teen_ep)
            logger.info(
                f"[MaturityPacingCalculator] Injected auto-durations into MaturityManager: CHILD={child_ep} eps, TEEN={teen_ep} eps"
            )
            return True

        return False
