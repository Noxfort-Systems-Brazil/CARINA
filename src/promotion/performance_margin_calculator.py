# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Performance Margin Calculator for Agent Graduation.

Calculates dynamic graduation performance margin (%) for TEEN -> ADULT promotion
using empirical road traffic fluid dynamics (speed ratio and space occupancy).
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class PerformanceMarginCalculator:
    """
    Calculates dynamic graduation performance margin (%) for TEEN -> ADULT promotion
    using empirical road traffic fluid dynamics (speed ratio and space occupancy).
    """

    DEFAULT_MARGIN_PERCENT: float = 10.0
    COUPLING_K: float = 0.25
    MIN_MARGIN_PERCENT: float = 3.0
    MAX_MARGIN_PERCENT: float = 25.0

    @classmethod
    def calculate_margin(
        cls,
        v_real: float,
        v_limit: float,
        occupancy: float,
        coupling_k: float = 0.25,
        min_margin: float = 3.0,
        max_margin: float = 25.0,
    ) -> float:
        """
        Calculates required graduation margin (%) continuously from fluid dynamics variables:
        delta* = K * (1 - v_real / v_limit) * (1 - occupancy) * 100%

        Args:
            v_real: Observed average speed (m/s or km/h, same unit as v_limit).
            v_limit: Maximum allowed speed for the road.
            occupancy: Average lane occupancy fraction [0.0, 1.0].
            coupling_k: Scaling coupling factor (default 0.25).
            min_margin: Minimum bounded margin percentage (default 3.0%).
            max_margin: Maximum bounded margin percentage (default 25.0%).

        Returns:
            Calculated margin percentage (e.g. 11.5 for 11.5%).
        """
        if v_limit <= 0.1:
            return cls.DEFAULT_MARGIN_PERCENT

        # 1. Inefficiency of legacy control: headroom between actual speed and speed limit
        speed_ratio = max(0.0, min(1.0, float(v_real) / float(v_limit)))
        inefficiency = max(0.05, 1.0 - speed_ratio)

        # 2. Physical free space headroom (1 - occupancy)
        occ_clamped = max(0.0, min(1.0, float(occupancy)))
        free_space = max(0.10, 1.0 - occ_clamped)

        # 3. Continuous graduation margin calculation
        raw_margin = float(coupling_k) * inefficiency * free_space * 100.0

        clamped_margin = max(float(min_margin), min(float(max_margin), raw_margin))
        return round(clamped_margin, 2)

    @classmethod
    def calculate_from_topology(cls, net: Any, settings: Any = None) -> float:
        """
        Estimates an initial baseline margin from road network topology properties.
        Used at map loading when live Synapse childhood telemetry is not yet accumulated.
        """
        if not net or not hasattr(net, "getEdges"):
            return cls.DEFAULT_MARGIN_PERCENT

        edges = net.getEdges()
        if not edges:
            return cls.DEFAULT_MARGIN_PERCENT

        speeds = [e.getSpeed() for e in edges if hasattr(e, "getSpeed") and e.getSpeed() > 0]
        avg_speed_limit = sum(speeds) / len(speeds) if speeds else 13.89

        # In uncalibrated networks, assume typical urban baseline speed is ~50% of speed limit
        # and baseline occupancy is ~35%
        return cls.calculate_margin(
            v_real=avg_speed_limit * 0.50,
            v_limit=avg_speed_limit,
            occupancy=0.35,
        )

    @classmethod
    def calculate_from_childhood_telemetry(
        cls,
        conn: Any,
        scenario_name: str = None,
        coupling_k: float = 0.25,
        min_margin: float = 3.0,
        max_margin: float = 25.0,
    ) -> float:
        """
        Calculates margin using empirical fluid dynamics recorded during the CHILD maturity phase
        from the synapse_fluid_dynamics table.
        """
        if not conn:
            return cls.DEFAULT_MARGIN_PERCENT

        try:
            cursor = conn.cursor()
            if scenario_name:
                try:
                    cursor.execute(
                        "SELECT AVG(mean_speed), AVG(speed_limit), AVG(occupancy) "
                        "FROM synapse_fluid_dynamics "
                        "WHERE maturity_stage = 'CHILD' AND speed_limit > 0.1 AND scenario_name = %s",
                        (scenario_name,),
                    )
                except Exception:
                    cursor.execute(
                        "SELECT AVG(mean_speed), AVG(speed_limit), AVG(occupancy) "
                        "FROM synapse_fluid_dynamics "
                        "WHERE maturity_stage = 'CHILD' AND speed_limit > 0.1 AND scenario_name = ?",
                        (scenario_name,),
                    )
            else:
                cursor.execute(
                    "SELECT AVG(mean_speed), AVG(speed_limit), AVG(occupancy) "
                    "FROM synapse_fluid_dynamics "
                    "WHERE maturity_stage = 'CHILD' AND speed_limit > 0.1"
                )

            row = cursor.fetchone()
            if row and row[0] is not None and row[1] is not None and row[2] is not None:
                v_real = float(row[0])
                v_limit = float(row[1])
                occupancy = float(row[2])
                return cls.calculate_margin(
                    v_real=v_real,
                    v_limit=v_limit,
                    occupancy=occupancy,
                    coupling_k=coupling_k,
                    min_margin=min_margin,
                    max_margin=max_margin,
                )
        except Exception as err:
            logger.warning(f"[PerformanceMarginCalculator] Error querying childhood telemetry: {err}", exc_info=True)

        return cls.DEFAULT_MARGIN_PERCENT

    @classmethod
    def apply_if_enabled(
        cls,
        maturity_manager: Any,
        margin_percent: float,
        settings: Any,
    ) -> bool:
        """
        If automatic performance margin calculation is enabled in settings,
        injects the calculated margin percentage into maturity_manager and promotion_evaluator.

        Returns:
            True if applied, False otherwise.
        """
        is_enabled = True
        if settings is not None:
            if hasattr(settings, "getboolean"):
                try:
                    is_enabled = settings.getboolean("MATURITY", "auto_performance_margin_enabled", fallback=True)
                except Exception:
                    is_enabled = True
            elif isinstance(settings, dict):
                val = str(settings.get("auto_performance_margin_enabled", "True")).lower()
                is_enabled = val in ("true", "1", "yes")

        if not is_enabled:
            return False

        if settings is not None:
            if hasattr(settings, "set") and hasattr(settings, "has_section"):
                if not settings.has_section("MATURITY"):
                    settings.add_section("MATURITY")
                settings.set("MATURITY", "performance_margin", str(margin_percent))
            elif isinstance(settings, dict):
                settings["performance_margin"] = str(margin_percent)

        if maturity_manager and hasattr(maturity_manager, "set_performance_margin"):
            maturity_manager.set_performance_margin(margin_percent)
            logger.info(
                f"[PerformanceMarginCalculator] Auto performance margin applied: {margin_percent:.2f}%"
            )
            return True

        return False
