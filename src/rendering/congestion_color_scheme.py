# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# File: src/rendering/congestion_color_scheme.py
# Author: Gabriel Moraes
# Date: September 2026

import math
from typing import Tuple


class CongestionColorScheme:
    """Provides color scale mappings for traffic congestion levels."""

    # Color scale used by services like Waze and Google Maps:
    # Dark Green -> Green -> Yellow -> Orange -> Orange Red -> Red
    COLOR_STOPS = [
        (0.0, (0, 100, 0)),  # Dark green - free flow
        (0.25, (0, 255, 0)),  # Green - light traffic
        (0.5, (255, 255, 0)),  # Yellow - moderate traffic
        (0.7, (255, 165, 0)),  # Orange - heavy traffic
        (0.85, (255, 69, 0)),  # Orange red - very heavy traffic
        (1.0, (255, 0, 0)),  # Red - severe congestion
    ]

    @classmethod
    def get_precise_color_for_congestion(
        cls, value: float, max_expected_value: float = 100.0
    ) -> Tuple[float, float, float]:
        """
        Converts congestion value to a normalized RGB tuple (0.0 to 1.0)
        using linear interpolation between color stops.
        """
        normalized = min(max(value / max_expected_value, 0.0), 1.0)
        return cls._interpolate_stops(normalized)

    @classmethod
    def get_enhanced_color_for_congestion(
        cls, value: float, max_expected_value: float = 100.0
    ) -> Tuple[float, float, float]:
        """
        Converts congestion value to a normalized RGB tuple using a non-linear
        curve to emphasize subtle variations at lower and higher traffic tiers.
        """
        normalized = min(max(value / max_expected_value, 0.0), 1.0)

        if normalized == 0:
            adjusted = 0.0
        elif normalized < 0.3:
            adjusted = math.pow(normalized / 0.3, 0.7) * 0.3
        elif normalized < 0.7:
            adjusted = 0.3 + ((normalized - 0.3) / 0.4) * 0.4
        else:
            adjusted = 0.7 + math.pow((normalized - 0.7) / 0.3, 1.3) * 0.3

        return cls._interpolate_stops(adjusted)

    @classmethod
    def _interpolate_stops(cls, adjusted: float) -> Tuple[float, float, float]:
        """Linearly interpolates RGB stops based on an adjusted (0.0 to 1.0) value."""
        for i in range(len(cls.COLOR_STOPS) - 1):
            start_stop, start_color = cls.COLOR_STOPS[i]
            end_stop, end_color = cls.COLOR_STOPS[i + 1]

            if start_stop <= adjusted <= end_stop:
                segment_normalized = (adjusted - start_stop) / (end_stop - start_stop)
                r = int(start_color[0] + (end_color[0] - start_color[0]) * segment_normalized)
                g = int(start_color[1] + (end_color[1] - start_color[1]) * segment_normalized)
                b = int(start_color[2] + (end_color[2] - start_color[2]) * segment_normalized)
                return (r / 255.0, g / 255.0, b / 255.0)

        r, g, b = cls.COLOR_STOPS[-1][1]
        return (r / 255.0, g / 255.0, b / 255.0)
