# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Base utilities and color interpolator for traffic heatmap renderers.
Decomposes color mapping math and image serialization according to SRP and Clean Architecture.
"""

import logging
import math
from typing import Any, Tuple

from rendering.mpl_utils import render_figure_to_base64


class HeatmapColorScaler:
    """
    Computes linear and enhanced (logarithmic) traffic congestion colors
    using Waze / Google Maps color stop standards.
    """

    COLOR_STOPS = [
        (0.0, (0, 100, 0)),  # Dark green - free traffic
        (0.25, (0, 255, 0)),  # Green - light traffic
        (0.5, (255, 255, 0)),  # Yellow - moderate traffic
        (0.7, (255, 165, 0)),  # Orange - heavy traffic
        (0.85, (255, 69, 0)),  # Orange red - very heavy traffic
        (1.0, (255, 0, 0)),  # Red - severe congestion
    ]

    @classmethod
    def interpolate_stops(cls, normalized_val: float) -> Tuple[int, int, int]:
        """Interpolates between predefined color stops for a value between 0.0 and 1.0."""
        for i in range(len(cls.COLOR_STOPS) - 1):
            if normalized_val >= cls.COLOR_STOPS[i][0] and normalized_val <= cls.COLOR_STOPS[i + 1][0]:
                start_val, start_rgb = cls.COLOR_STOPS[i]
                end_val, end_rgb = cls.COLOR_STOPS[i + 1]

                segment_norm = (normalized_val - start_val) / (end_val - start_val)
                r = int(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * segment_norm)
                g = int(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * segment_norm)
                b = int(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * segment_norm)
                return (r, g, b)

        return cls.COLOR_STOPS[-1][1]

    @classmethod
    def get_linear_rgb(cls, value: float, max_expected_value: float = 100.0) -> Tuple[int, int, int]:
        """Returns 0-255 RGB tuple for value with linear interpolation."""
        normalized = min(max(value / max_expected_value, 0.0), 1.0)
        return cls.interpolate_stops(normalized)

    @classmethod
    def get_enhanced_rgb(cls, value: float, max_expected_value: float = 100.0) -> Tuple[int, int, int]:
        """Returns 0-255 RGB tuple with smoothed logarithmic adjustment."""
        normalized = min(max(value / max_expected_value, 0.0), 1.0)
        if normalized == 0:
            adjusted = 0.0
        elif normalized < 0.3:
            adjusted = math.pow(normalized / 0.3, 0.7) * 0.3
        elif normalized < 0.7:
            adjusted = 0.3 + ((normalized - 0.3) / 0.4) * 0.4
        else:
            adjusted = 0.7 + math.pow((normalized - 0.7) / 0.3, 1.3) * 0.3
        return cls.interpolate_stops(adjusted)

    @staticmethod
    def rgb_to_normalized_tuple(rgb: Tuple[int, int, int]) -> Tuple[float, float, float]:
        """Converts (0-255) RGB to (0.0-1.0) float tuple for matplotlib."""
        return (rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0)

    @staticmethod
    def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
        """Converts (0-255) RGB to hexadecimal color string."""
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def save_figure_to_base64(fig: Any, ax: Any, dpi: int = 80) -> str:
    """Renders and encodes a matplotlib figure into a base64 PNG string."""
    return render_figure_to_base64(
        fig,
        close_fig=True,
        format="png",
        dpi=dpi,
        facecolor=ax.get_facecolor(),
        bbox_inches="tight",
        pad_inches=0.02,
        edgecolor="none",
    )
