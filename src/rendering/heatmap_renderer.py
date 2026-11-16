# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import threading
from typing import TYPE_CHECKING

# --- CHANGE 1: Add imports ---
if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

from rendering.mpl_utils import close_offscreen_figure, create_offscreen_figure, render_figure_to_base64


class HeatmapRenderer:
    """The specialist in rendering dynamic heatmaps in memory with performance optimizations."""

    def __init__(self, locale_manager: "LocaleManagerBackend"):
        """Initializes the heatmap renderer."""
        self.locale_manager = locale_manager
        # Simple cache to avoid unnecessary renders
        self._cache = {}
        self._cache_size_limit = 5
        # Lock to protect cache access
        self._cache_lock = threading.Lock()
        # --- CHANGE 3 ---
        logging.info(self.locale_manager.get_string("heatmap_renderer.init.created"))

    def create_heatmap_image_in_memory(
        self, map_data: tuple, congestion_data: dict, saturation_threshold: float = 100.0
    ) -> str | None:
        """
        Generates a map image with streets colored by congestion level
        and returns it as a Base64 string.

        This version includes performance optimizations:
        - Cache of previous renders
        - Reduced resolution for higher speed
        - Simplified rendering pipeline
        """
        lm = self.locale_manager

        try:
            # Create cache key based on congestion data
            cache_key = self._generate_cache_key(congestion_data, saturation_threshold)

            # Check if it already exists in cache
            with self._cache_lock:
                if cache_key in self._cache:
                    return self._cache[cache_key]

            nodes, edges = map_data

            # Use smaller figure for higher speed
            fig, ax = create_offscreen_figure((4.0, 2.4), dpi=80)  # Reduced size and DPI for speed
            try:
                threshold = max(saturation_threshold, 1.0)

                # Optimization: only process edges with congestion data
                congestion_edges = {k for k in congestion_data.keys()}

                for edge in edges:
                    edge_id = edge.get("id", "")

                    # Only process edges with congestion data
                    if edge_id not in congestion_edges:
                        continue

                    congestion_index = congestion_data.get(edge_id, 0.0)

                    # Use the new improved function to get more precise colors
                    rgb_color = self.get_enhanced_color_for_congestion(congestion_index, threshold)
                    color = rgb_color

                    shape = edge["shape"]
                    if len(shape) < 2:
                        continue

                    x_coords, y_coords = zip(*shape)

                    # Reduce width and quality for higher speed
                    ax.plot(
                        x_coords,
                        y_coords,
                        color=color,
                        linewidth=1.5,  # Linewidth reduzido
                        zorder=1,
                        solid_capstyle="round",
                        antialiased=False,  # Disable anti-aliasing for speed
                    )

                # Draw nodes if they exist, with reduced size
                if nodes:
                    node_x = [n["x"] for n in nodes.values() if "x" in n and "y" in n]
                    node_y = [n["y"] for n in nodes.values() if "x" in n and "y" in n]
                    if node_x and node_y:
                        ax.scatter(
                            node_x, node_y, s=5, color="#808080", zorder=2, alpha=0.7
                        )  # Reduced size and opacity

                ax.set_aspect("equal", adjustable="box")
                # Remove axes for speed
                ax.set_xticks([])
                ax.set_yticks([])
                ax.axis("off")
                ax.set_facecolor("#F7F7F7")

                image_base64 = render_figure_to_base64(
                    fig,
                    close_fig=False,
                    format="png",
                    dpi=80,
                    facecolor=ax.get_facecolor(),
                    bbox_inches="tight",
                    pad_inches=0.02,
                    edgecolor="none",
                )
            finally:
                close_offscreen_figure(fig)

            # Store in cache
            with self._cache_lock:
                if len(self._cache) >= self._cache_size_limit:
                    # Remove oldest item if cache is full
                    oldest_key = next(iter(self._cache))
                    del self._cache[oldest_key]
                self._cache[cache_key] = image_base64

            return image_base64

        except Exception as e:
            # --- CHANGE 4 ---
            logging.error(lm.get_string("heatmap_renderer.run.error", error=e), exc_info=True)
            return None

    def _generate_cache_key(self, congestion_data: dict, threshold: float) -> str:
        """Generates a cache key based on congestion data."""
        # Create a simplified representation of the data for the key
        total_congestion = sum(congestion_data.values()) if congestion_data else 0
        edge_count = len(congestion_data)
        return f"{total_congestion:.2f}_{edge_count}_{threshold}"

    def get_precise_color_for_congestion(self, value: float, max_expected_value: float = 100.0) -> tuple:
        """
        Converts a congestion value into an RGB tuple with high precision.
        Implements a color scale similar to those used by Waze and Google Maps.

        Args:
            value: Congestion value to convert
            max_expected_value: Maximum expected value (for normalization)

        Returns:
            RGB tuple representing the appropriate color
        """
        # Normalize the value between 0 and 1, considering the maximum expected value
        normalized = min(max(value / max_expected_value, 0.0), 1.0)

        # Color scale used by services like Waze and Google Maps:
        # Dark green (free traffic) -> Green -> Yellow -> Orange -> Red -> Purple (extreme congestion)
        color_stops = [
            (0.0, (0, 100, 0)),  # Dark green - free traffic
            (0.25, (0, 255, 0)),  # Green - light traffic
            (0.5, (255, 255, 0)),  # Yellow - moderate traffic
            (0.7, (255, 165, 0)),  # Orange - heavy traffic
            (0.85, (255, 69, 0)),  # Orange red - very heavy traffic
            (1.0, (255, 0, 0)),  # Red - severe congestion
        ]

        # Find between which control points the normalized value is
        for i in range(len(color_stops) - 1):
            if normalized >= color_stops[i][0] and normalized <= color_stops[i + 1][0]:
                # Calculate the fraction between the two control points
                start_value, start_color = color_stops[i]
                end_value, end_color = color_stops[i + 1]

                # Normalize again between the two control points
                segment_normalized = (normalized - start_value) / (end_value - start_value)

                # Linearly interpolate between the two colors
                r = int(start_color[0] + (end_color[0] - start_color[0]) * segment_normalized)
                g = int(start_color[1] + (end_color[1] - start_color[1]) * segment_normalized)
                b = int(start_color[2] + (end_color[2] - start_color[2]) * segment_normalized)

                return (r / 255.0, g / 255.0, b / 255.0)  # Returns normalized values for matplotlib

        # Special case for the last interval
        r, g, b = color_stops[-1][1]
        return (r / 255.0, g / 255.0, b / 255.0)

    def get_enhanced_color_for_congestion(self, value: float, max_expected_value: float = 100.0) -> tuple:
        """
        Converts a congestion value into an RGB tuple with an advanced scale.
        Uses a logarithmic curve for improved representation of small variations.

        Args:
            value: Congestion value to convert
            max_expected_value: Maximum expected value (for normalization)

        Returns:
            RGB tuple representing the appropriate color
        """
        import math

        # Normalize value
        normalized = min(max(value / max_expected_value, 0.0), 1.0)

        # Apply a smoothed logarithmic transformation to highlight small variations
        if normalized == 0:
            adjusted = 0
        else:
            # Use a combination of functions to highlight variations in different ranges
            if normalized < 0.3:
                # Increase sensitivity for low values
                adjusted = math.pow(normalized / 0.3, 0.7) * 0.3
            elif normalized < 0.7:
                # Maintain average linearity for intermediate range
                adjusted = 0.3 + ((normalized - 0.3) / 0.4) * 0.4
            else:
                # Adjust to highlight high values
                adjusted = 0.7 + math.pow((normalized - 0.7) / 0.3, 1.3) * 0.3

        # Now use the standardized color scale
        color_stops = [
            (0.0, (0, 100, 0)),  # Dark green - free traffic
            (0.25, (0, 255, 0)),  # Green - light traffic
            (0.5, (255, 255, 0)),  # Yellow - moderate traffic
            (0.7, (255, 165, 0)),  # Orange - heavy traffic
            (0.85, (255, 69, 0)),  # Orange red - very heavy traffic
            (1.0, (255, 0, 0)),  # Red - severe congestion
        ]

        # Find between which control points the adjusted value is
        for i in range(len(color_stops) - 1):
            if adjusted >= color_stops[i][0] and adjusted <= color_stops[i + 1][0]:
                # Calculate the fraction between the two control points
                start_value, start_color = color_stops[i]
                end_value, end_color = color_stops[i + 1]

                # Normalize again between the two control points
                segment_normalized = (adjusted - start_value) / (end_value - start_value)

                # Linearly interpolate between the two colors
                r = int(start_color[0] + (end_color[0] - start_color[0]) * segment_normalized)
                g = int(start_color[1] + (end_color[1] - start_color[1]) * segment_normalized)
                b = int(start_color[2] + (end_color[2] - start_color[2]) * segment_normalized)

                return (r / 255.0, g / 255.0, b / 255.0)  # Returns normalized values for matplotlib

        # Special case for the last interval
        r, g, b = color_stops[-1][1]
        return (r / 255.0, g / 255.0, b / 255.0)

    def clear_cache(self):
        """Clears the render cache."""
        with self._cache_lock:
            self._cache.clear()
