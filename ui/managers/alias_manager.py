# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import logging
import os
import shutil

from src.utils.paths import get_user_config_dir, resource_path


class AliasManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AliasManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.filepath = os.path.join(get_user_config_dir(), "aliases.json")

        # Migration from old path (config/aliases.json relative to project root)
        old_filepath = resource_path(os.path.join("config", "aliases.json"))
        if not os.path.exists(self.filepath) and os.path.exists(old_filepath):
            try:
                shutil.copy2(old_filepath, self.filepath)
                logging.info(f"[AliasManager] Migrated aliases.json from {old_filepath} to {self.filepath}")
            except Exception as e:
                logging.error(f"[AliasManager] Failed to migrate aliases.json: {e}", exc_info=True)

        self.aliases = {}
        self.default_aliases = {}
        self.load()
        self._initialized = True

    def register_default_alias(self, original_id: str, default_name: str) -> None:
        """Registers a default friendly name (e.g., from SUMO road network) without overriding user customizations."""
        if original_id and default_name and default_name != original_id:
            self.default_aliases[str(original_id)] = str(default_name)

    def register_default_aliases(self, mapping: dict[str, str]) -> None:
        """Registers multiple default friendly names at once."""
        for orig_id, name in mapping.items():
            self.register_default_alias(orig_id, name)

    def load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self.aliases = json.load(f)
            except Exception as e:
                logging.error(f"[AliasManager] Error loading aliases: {e}", exc_info=True)
                self.aliases = {}

    def save(self):
        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.aliases, f, indent=4)
        except Exception as e:
            logging.error(f"[AliasManager] Error saving aliases: {e}", exc_info=True)

    def get_alias(self, original_id: str, default: str | None = None) -> str:
        """
        Returns the friendly name of the element.
        Priority:
        1. User-customized alias (aliases.json)
        2. default provided by caller
        3. Default name extracted from network mesh (default_aliases)
        4. Intelligent lane resolution (e.g. 'Main St [Lane 0]')
        5. Original ID
        """
        orig_str = str(original_id)
        if orig_str in self.aliases:
            return self.aliases[orig_str]

        if default is not None and str(default).strip() and str(default) != orig_str:
            return str(default)

        if orig_str in self.default_aliases:
            return self.default_aliases[orig_str]

        # SUMO lane resolution (<edge_id>_<lane_index>)
        if "_" in orig_str:
            edge_id, _, lane_idx = orig_str.rpartition("_")
            if lane_idx.isdigit():
                parent_alias = self.get_alias(edge_id, default=None)
                if parent_alias != edge_id:
                    return f"{parent_alias} [Faixa {lane_idx}]"

        return orig_str

    def set_alias(self, original_id: str, alias: str):
        orig_str = str(original_id)
        clean_alias = alias.strip() if alias else ""

        # If alias is empty or identical to mesh default, remove customization
        if not clean_alias or clean_alias == self.default_aliases.get(orig_str):
            if orig_str in self.aliases:
                del self.aliases[orig_str]
        else:
            self.aliases[orig_str] = clean_alias
        self.save()
