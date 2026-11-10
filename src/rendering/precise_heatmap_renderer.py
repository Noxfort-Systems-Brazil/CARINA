# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import threading
from typing import TYPE_CHECKING

import matplotlib.pyplot as plt

from rendering.heatmap_base_renderer import HeatmapColorScaler, save_figure_to_base64

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend


class PreciseHeatmapRenderer:
    """Heatmap renderer with high precision for congestion values."""

    def __init__(self, locale_manager: "LocaleManagerBackend"):
        """Initializes the precise heatmap renderer."""
        self.locale_manager = locale_manager
        # Simple cache to avoid unnecessary renders
        self._cache = {}
        self._cache_size_limit = 5
        # Lock to protect cache access
        self._cache_lock = threading.Lock()

        logging.info(self.locale_manager.get_string("precise_heatmap_renderer.init.created"))

    def create_heatmap_image_in_memory(
        self, map_data: tuple, congestion_data: dict, saturation_threshold: float = 100.0
    ) -> str | None:
        """
        Generates a map image with streets colored by congestion level
        and returns it as a Base64 string.
        """
        lm = self.locale_manager

        try:
            cache_key = self._generate_cache_key(congestion_data, saturation_threshold)

            with self._cache_lock:
                if cache_key in self._cache:
                    return self._cache[cache_key]

            nodes, edges = map_data
            fig, ax = plt.subplots(figsize=(4.0, 2.4), dpi=80)
            cmap = plt.get_cmap("viridis")
            threshold = max(saturation_threshold, 1.0)

            for edge in edges:
                edge_id = edge.get("id", "")
                congestion_value = congestion_data.get(edge_id, 0.0)

                if isinstance(congestion_value, dict):
                    congestion_value = congestion_value.get("congestion", 0.0)

                normalized_congestion = min(max(congestion_value / threshold, 0.0), 1.0)
                color = cmap(normalized_congestion)

                shape = edge.get("shape", [])
                if len(shape) < 2:
                    continue

                x_coords, y_coords = zip(*shape)
                ax.plot(
                    x_coords,
                    y_coords,
                    color=color,
                    linewidth=1.5,
                    zorder=1,
                    solid_capstyle="round",
                    antialiased=False,
                )

            if nodes:
                node_x = [n["x"] for n in nodes.values() if "x" in n and "y" in n]
                node_y = [n["y"] for n in nodes.values() if "x" in n and "y" in n]
                if node_x and node_y:
                    ax.scatter(node_x, node_y, s=5, color="#808080", zorder=2, alpha=0.7)

            ax.set_aspect("equal", adjustable="box")
            ax.set_xticks([])
            ax.set_yticks([])
            ax.axis("off")
            ax.set_facecolor("#F7F7F7")

            image_base64 = save_figure_to_base64(fig, ax, dpi=80)

            with self._cache_lock:
                if len(self._cache) >= self._cache_size_limit:
                    oldest_key = next(iter(self._cache))
                    del self._cache[oldest_key]
                self._cache[cache_key] = image_base64

            return image_base64

        except Exception as e:
            logging.error(lm.get_string("precise_heatmap_renderer.run.error", error=e), exc_info=True)
            return None

    def _generate_cache_key(self, congestion_data: dict, threshold: float) -> str:
        """Generates a cache key based on congestion data."""
        sorted_keys = sorted(congestion_data.keys())
        key_parts = [str(congestion_data[k]) for k in sorted_keys[:10]]
        key_content = "_".join(key_parts)
        return f"{key_content}_{threshold}"

    def clear_cache(self):
        """Clears the render cache."""
        with self._cache_lock:
            self._cache.clear()

    def get_precise_color_for_congestion(self, value: float, max_expected_value: float = 100.0) -> str:
        """Converts a congestion value into a hexadecimal color with high precision."""
        rgb = HeatmapColorScaler.get_linear_rgb(value, max_expected_value)
        return HeatmapColorScaler.rgb_to_hex(rgb)

    def get_enhanced_color_for_congestion(self, value: float, max_expected_value: float = 100.0) -> str:
        """Converts a congestion value into a hexadecimal color with an advanced scale."""
        rgb = HeatmapColorScaler.get_enhanced_rgb(value, max_expected_value)
        return HeatmapColorScaler.rgb_to_hex(rgb)
