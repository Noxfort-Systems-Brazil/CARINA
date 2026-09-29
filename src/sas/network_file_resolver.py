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

# File: src/sas/network_file_resolver.py
# Author: Gabriel Moraes
# Date: September 2026

import json
import logging
import os
from typing import Optional

from src.utils.paths import get_base_output_dir, get_user_config_dir


class NetworkFileResolver:
    """
    Resolves the network topology map file path for an active scenario,
    incorporating multi-tier fallback searching and disk persistence.
    """

    @classmethod
    def save_last_known_net_file(cls, path: str) -> None:
        """Saves the last successfully used network map file path to user configuration."""
        if not path or not os.path.exists(path):
            return
        try:
            config_dir = get_user_config_dir()
            persist_file = os.path.join(config_dir, "last_net_file.json")
            with open(persist_file, "w", encoding="utf-8") as f:
                json.dump({"last_net_file_path": path}, f, indent=4)
            logging.debug(f"[NetworkFileResolver] Persisted last known net_file_path: {path}")
        except Exception as e:
            logging.error(f"[NetworkFileResolver] Failed to persist net_file_path: {e}")

    @classmethod
    def load_last_known_net_file(cls) -> Optional[str]:
        """Loads the last successfully used network map file path from user configuration."""
        try:
            config_dir = get_user_config_dir()
            persist_file = os.path.join(config_dir, "last_net_file.json")
            if os.path.exists(persist_file):
                with open(persist_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    path = data.get("last_net_file_path")
                    if path and os.path.exists(path):
                        logging.info(f"[NetworkFileResolver] Restored net_file_path from config: {path}")
                        return path
        except Exception as e:
            logging.error(f"[NetworkFileResolver] Failed to load persisted net_file_path: {e}")
        return None

    @classmethod
    def resolve_net_file_path(cls, scenario_name: str) -> Optional[str]:
        """
        Attempts to locate the map file (.net.xml) for the active scenario with 4 fallback levels.
        """
        # Level 1: Look in the scenario's results/maps folder
        try:
            maps_dir = os.path.join(get_base_output_dir(), "results", scenario_name, "maps")
            if os.path.exists(maps_dir):
                for f in os.listdir(maps_dir):
                    if f.endswith(".net.xml") or f.endswith(".net.xml.gz"):
                        resolved_path = os.path.join(maps_dir, f)
                        cls.save_last_known_net_file(resolved_path)
                        return resolved_path
        except Exception as e:
            logging.error(f"[NetworkFileResolver] Error checking scenario maps for {scenario_name}: {e}")

        # Level 2: Try to load from persistent user configuration
        persisted_path = cls.load_last_known_net_file()
        if persisted_path:
            return persisted_path

        # Level 3: Scan the whole results directory recursively
        try:
            results_dir = os.path.join(get_base_output_dir(), "results")
            if os.path.exists(results_dir):
                logging.info(f"[NetworkFileResolver] Scanning {results_dir} recursively for net.xml files...")
                for root, _, files in os.walk(results_dir):
                    for f in files:
                        if f.endswith(".net.xml") or f.endswith(".net.xml.gz"):
                            fallback_path = os.path.join(root, f)
                            cls.save_last_known_net_file(fallback_path)
                            return fallback_path
        except Exception as e:
            logging.error(f"[NetworkFileResolver] Error scanning results directory: {e}")

        # Level 4: Scan parent/workspace directories
        try:
            base_dir = get_base_output_dir()
            parent_dir = os.path.dirname(base_dir) if base_dir else None
            search_dirs = [base_dir, parent_dir] if parent_dir else [base_dir]
            for search_dir in search_dirs:
                if search_dir and os.path.exists(search_dir):
                    for root, _, files in os.walk(search_dir):
                        if ".venv" in root or ".git" in root or "node_modules" in root:
                            continue
                        for f in files:
                            if f.endswith(".net.xml") or f.endswith(".net.xml.gz"):
                                fallback_path = os.path.join(root, f)
                                cls.save_last_known_net_file(fallback_path)
                                return fallback_path
        except Exception as e:
            logging.error(f"[NetworkFileResolver] Error scanning workspace directory: {e}")

        return None
