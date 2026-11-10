# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Handles logging commanded traffic light stage colors and manual overrides to carina_colors.log.
Isolated responsibility according to the Single Responsibility Principle (SRP).
"""

import logging
import os
from typing import Any, Dict, Optional

from src.utils.paths import get_base_output_dir

logger = logging.getLogger(__name__)


class TrafficColorLogger:
    """
    Dedicated auditor and logger for traffic signal display states in SUMO-compliant format.
    """

    @staticmethod
    def _get_log_filepath() -> str:
        log_dir = os.path.join(get_base_output_dir(), "logs")
        os.makedirs(log_dir, exist_ok=True)
        return os.path.join(log_dir, "carina_colors.log")

    @classmethod
    def log_stage(
        cls,
        intersection_id: str,
        current_stage_idx: int,
        active_states: Dict[int, str],
        locale_manager: Optional[Any] = None,
    ) -> None:
        """
        Logs commanded stage state string to carina_colors.log in SUMO format.
        """

        def _get_string(key: str, default: str = None, **kwargs) -> str:
            if locale_manager and hasattr(locale_manager, "get_string"):
                return locale_manager.get_string(key, default=default, **kwargs)
            return default.format(**kwargs) if default and kwargs else (default or key)

        if not active_states or current_stage_idx not in active_states:
            return

        try:
            log_file = cls._get_log_filepath()
            state_str = active_states[current_stage_idx]
            if state_str and all(c.lower() == "r" for c in state_str):
                stage_num = 0
            else:
                stage_num = current_stage_idx + 1

            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"estágio {stage_num}: {state_str}\n")
        except Exception as e:
            logger.error(
                _get_string(
                    "drivers.traffic_light.colors_log_error",
                    default="[Intersection {id}] Error writing to carina_colors.log: {error}",
                    id=intersection_id,
                    error=e,
                )
            , exc_info=True)

    @classmethod
    def log_override(
        cls,
        intersection_id: str,
        override_type: str,
        locale_manager: Optional[Any] = None,
    ) -> None:
        """
        Logs a manual override (flash or dark/desligado) to carina_colors.log.
        """

        def _get_string(key: str, default: str = None, **kwargs) -> str:
            if locale_manager and hasattr(locale_manager, "get_string"):
                return locale_manager.get_string(key, default=default, **kwargs)
            return default.format(**kwargs) if default and kwargs else (default or key)

        label = "flash" if override_type == "ALERT" else "desligado"
        try:
            log_file = cls._get_log_filepath()
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"estágio {label}: {label}\n")
        except Exception as e:
            logger.error(
                _get_string(
                    "drivers.traffic_light.override_log_error",
                    default="[Intersection {id}] Error writing override to carina_colors.log: {error}",
                    id=intersection_id,
                    error=e,
                )
            , exc_info=True)
