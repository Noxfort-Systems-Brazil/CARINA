# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later
from typing import Any, Dict, List


class MFDZoneCalculator:
    """
    Responsibility: Calculate the distribution of time spent in MFD operational zones
    (Green: uncongested, Yellow: optimal capacity, Red: gridlock/congestion).
    """

    @staticmethod
    def calculate_zone_distribution(history: List[Dict[str, Any]], peak_accum: float) -> Dict[str, float]:
        """
        Compute percentage of simulation history spent in Green, Yellow, and Red MFD accumulation zones.

        :param history: List of historical network state dictionaries
        :param peak_accum: Critical accumulation threshold (N_crit)
        :return: Dict containing green_zone_pct, yellow_zone_pct, and red_zone_pct
        """
        if not history or peak_accum <= 0:
            return {"green_zone_pct": 33.3, "yellow_zone_pct": 33.3, "red_zone_pct": 33.4}

        green_count = 0
        yellow_count = 0
        red_count = 0
        total = len(history)

        ncrit = peak_accum if peak_accum > 0 else 500.0

        for pt in history:
            acc = pt.get("accumulation", 0.0)
            if acc < 0.7 * ncrit:
                green_count += 1
            elif acc <= 1.1 * ncrit:
                yellow_count += 1
            else:
                red_count += 1

        return {
            "green_zone_pct": round((green_count / total) * 100.0, 1),
            "yellow_zone_pct": round((yellow_count / total) * 100.0, 1),
            "red_zone_pct": round((red_count / total) * 100.0, 1),
        }
