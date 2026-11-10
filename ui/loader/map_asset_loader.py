# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Defines the MapAssetLoader.
Acts as a unified facade coordinating asset path resolution, map topology extraction, and basemap assets.
"""

import base64
import json
import logging
import os
from typing import Any, Dict, Tuple

from ui.loader.map_asset_path_resolver import MapAssetPathResolver
from ui.loader.map_topology_loader import MapTopologyLoader


class MapAssetLoader:
    """Finds and loads asset files from the most recent simulation."""

    def __init__(self):
        """Initializes the asset loader and its path resolver."""
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self._path_resolver = MapAssetPathResolver(self.project_root)

    def _has_map_files(self, folder_path: str) -> bool:
        return self._path_resolver.has_map_files(folder_path)

    def _find_latest_scenario_dir(self) -> str | None:
        return self._path_resolver.find_latest_scenario_dir()

    def get_asset_path(self, asset_type: str, asset_filename: str) -> str | None:
        return self._path_resolver.get_asset_path(asset_type, asset_filename)

    def _try_load_from_scenario_dir(self, scenario_dir: str) -> Tuple[Dict, Any, Dict] | None:
        return MapTopologyLoader.load_topology(scenario_dir)

    def _register_default_aliases(self, edges_list: list) -> None:
        MapTopologyLoader.register_default_aliases(edges_list)

    def load_coordinates(self) -> Dict[str, Any] | None:
        """Finds and loads the content of the coordinates file from hft_live_session."""
        coords_path = self.get_asset_path("maps", "map_coords.json")
        if not coords_path:
            logging.error("[AssetLoader] Não foi possível encontrar o arquivo 'map_coords.json'.")
            return None

        try:
            with open(coords_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"[AssetLoader] Falha ao ler ou processar 'map_coords.json': {e}", exc_info=True)
            return None

    def ensure_basemap_present(self) -> str | None:
        """Ensures that basemap_positron.png exists in the active scenario maps directory."""
        try:
            from src.rendering.cartodb_basemap_fetcher import CartoDBBasemapFetcher

            if not CartoDBBasemapFetcher.ENABLED:
                return None

            scenario_dir = self._find_latest_scenario_dir()
            if not scenario_dir:
                return None
            maps_dir = os.path.join(scenario_dir, "maps") if os.path.exists(os.path.join(scenario_dir, "maps")) else scenario_dir
            basemap_path = os.path.join(maps_dir, "basemap_positron.png")
            if os.path.exists(basemap_path) and os.path.getsize(basemap_path) > 0:
                return basemap_path

            candidates = []
            for d in (maps_dir, scenario_dir):
                if os.path.exists(d):
                    for f in os.listdir(d):
                        if f.endswith(".net.xml.gz") or f.endswith(".net.xml"):
                            candidates.append(os.path.join(d, f))

            if candidates:
                net_file_path = candidates[0]
                from src.utils.sumo_geo_bounds_reader import SumoGeoBoundsReader

                geo_bounds = SumoGeoBoundsReader.read_bounds(net_file_path)
                if geo_bounds and geo_bounds.has_geo_coords:
                    return CartoDBBasemapFetcher.fetch_basemap(geo_bounds, maps_dir)
        except Exception as e:
            logging.warning(f"[AssetLoader] Erro ao assegurar basemap: {e}", exc_info=True)
        return None

    def load_map_data(self) -> Tuple[Dict, Any, Dict] | None:
        """Loads map data exclusively from the hft_live_session directory."""
        scenario_dir = self._find_latest_scenario_dir()
        if not scenario_dir:
            logging.error("[AssetLoader] Diretório hft_live_session não encontrado.")
            return None

        res = self._try_load_from_scenario_dir(scenario_dir)
        if res:
            from src.rendering.cartodb_basemap_fetcher import CartoDBBasemapFetcher

            if CartoDBBasemapFetcher.ENABLED:
                self.ensure_basemap_present()
            return res

        logging.error(
            "[AssetLoader] Falha ao encontrar mapa válido em hft_live_session (.net.xml.gz, .net.xml ou map_topology.json)."
        )
        return None

    def load_background_map(self) -> tuple[str, dict] | None:
        """Finds and loads the background map image (Base64) and its coordinates."""
        bg_json_path = self.get_asset_path("maps", "map_background.json")
        bg_png_path = self.get_asset_path("maps", "map_background.png")
        if not bg_json_path or not bg_png_path:
            logging.debug("[AssetLoader] Arquivos de imagem de fundo ou coordenadas não encontrados.")
            return None

        try:
            with open(bg_json_path, "r", encoding="utf-8") as f:
                bg_data = json.load(f)
            with open(bg_png_path, "rb") as f:
                b64_string = base64.b64encode(f.read()).decode("utf-8")
            return b64_string, bg_data
        except Exception as e:
            logging.error(f"[AssetLoader] Falha ao carregar mapa de fundo: {e}", exc_info=True)
            return None
