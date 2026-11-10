# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import os
from typing import TYPE_CHECKING

# --- CHANGE 1: Add imports ---
if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

# Import the new specialized classes from the new render folder
from rendering.heatmap_renderer import HeatmapRenderer
from rendering.precise_heatmap_renderer import PreciseHeatmapRenderer
from rendering.static_map_renderer import StaticMapRenderer


class AssetManager:
    """The Asset Manager that delegates rendering tasks to specialists."""

    # --- CHANGE 2: Modify the constructor ---
    def __init__(self, locale_manager: "LocaleManagerBackend"):
        """
        Initializes the AssetManager and its internal specialist renderers.
        """
        self.locale_manager = locale_manager
        self.static_map_renderer = StaticMapRenderer(locale_manager)
        self.heatmap_renderer = PreciseHeatmapRenderer(locale_manager)  # Use the precise renderer
        # --- CHANGE 3 ---
        logging.info(self.locale_manager.get_string("asset_manager.init.created"))

    def create_heatmap_image_in_memory(self, map_data: tuple, congestion_data: dict) -> str | None:
        """
        Delegates the heat map image generation to the specialist.
        """
        return self.heatmap_renderer.create_heatmap_image_in_memory(map_data=map_data, congestion_data=congestion_data)

    def clear_heatmap_cache(self):
        """
        Clears the heatmap renderer cache.
        """
        if hasattr(self.heatmap_renderer, "clear_cache"):
            self.heatmap_renderer.clear_cache()

    def create_map_with_icons(
        self, net_file_path: str, scenario_results_dir: str, icon_requests: dict, output_filename: str
    ) -> tuple[str | None, tuple | None]:
        """
        Delegates the static map with icons generation to the specialist.
        """
        return self.static_map_renderer.create_map_with_icons(
            net_file_path=net_file_path,
            scenario_results_dir=scenario_results_dir,
            icon_requests=icon_requests,
            output_filename=output_filename,
        )

    def generate_coordinates_file(
        self, map_data: tuple, traffic_light_ids: list, scenario_results_dir: str
    ) -> str | None:
        """
        Delegates the coordinates data file generation to the specialist.
        """
        return self.static_map_renderer.generate_coordinates_file(
            map_data=map_data,
            traffic_light_ids=traffic_light_ids,
            scenario_results_dir=scenario_results_dir,
            image_width=3840,
            image_height=2160,
        )

    def ensure_basemap(self, net_file_path: str, scenario_results_dir: str) -> str | None:
        """
        Ensures the CartoDB Positron basemap is generated/cached in the scenario directory.
        """
        try:
            from rendering.cartodb_basemap_fetcher import CartoDBBasemapFetcher
            from utils.sumo_geo_bounds_reader import SumoGeoBoundsReader

            maps_dir = os.path.join(scenario_results_dir, "maps")
            os.makedirs(maps_dir, exist_ok=True)
            geo_bounds = SumoGeoBoundsReader.read_bounds(net_file_path)
            if geo_bounds and geo_bounds.has_geo_coords:
                return CartoDBBasemapFetcher.fetch_basemap(geo_bounds, maps_dir)
        except Exception as e:
            logging.warning(f"[AssetManager] Erro ao assegurar basemap: {e}", exc_info=True)
        return None

