# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import os
from typing import Optional


class MapAssetPathResolver:
    """Specialized service for resolving paths and directories for simulation and map assets."""

    def __init__(self, project_root: Optional[str] = None):
        self.project_root = project_root or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )

    def has_map_files(self, folder_path: str) -> bool:
        """Checks if a directory (or its maps subfolder) contains supported map files."""
        if not os.path.exists(folder_path):
            return False
        candidates = [folder_path]
        maps_sub = os.path.join(folder_path, "maps")
        if os.path.exists(maps_sub):
            candidates.insert(0, maps_sub)

        for cand in candidates:
            try:
                for f in os.listdir(cand):
                    if (
                        f == "map_topology.json"
                        or f.endswith(".net.xml.gz")
                        or f.endswith(".net.xml")
                        or f.endswith(".nod.xml")
                    ):
                        return True
            except Exception:
                continue
        return False

    def find_latest_scenario_dir(self) -> str | None:
        """Returns exclusively the path to the hft_live_session directory."""
        try:
            from src.utils.paths import get_base_output_dir

            hft_dir = os.path.join(get_base_output_dir(), "results", "hft_live_session")
            if not os.path.exists(hft_dir):
                os.makedirs(hft_dir, exist_ok=True)
            return hft_dir
        except Exception as e:
            logging.error(f"[MapAssetPathResolver] Erro ao obter diretório hft_live_session: {e}", exc_info=True)
            return None

    def get_asset_path(self, asset_type: str, asset_filename: str) -> str | None:
        """Builds the path to a specific asset exclusively within the hft_live_session."""
        scenario_dir = self.find_latest_scenario_dir()
        if scenario_dir:
            asset_path = os.path.join(scenario_dir, asset_type, asset_filename)
            if os.path.exists(asset_path):
                return asset_path
            direct_path = os.path.join(scenario_dir, asset_filename)
            if os.path.exists(direct_path):
                return direct_path
        return None
