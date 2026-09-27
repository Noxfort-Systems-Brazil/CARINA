# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
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

# File: src/xai/xai_template_repository.py
# Author: Gabriel Moraes
# Date: August 14, 2026

import json
import logging
import os
from typing import Any, Dict, Optional


class XaiTemplateRepository:
    """
    Central repository for modular XAI configuration files and localized report templates.
    Fulfills Single Responsibility Principle (SRP) and Open-Closed Principle (OCP)
    by aggregating modular JSON configurations with in-memory caching.
    """

    _cached_templates: Optional[Dict[str, Any]] = None
    _cached_categories: Optional[Dict[str, Any]] = None

    CONFIG_FILES = [
        "xai_report_sections.json",
        "xai_equations.json",
        "xai_categories.json",
        "xai_table_templates.json",
        "xai_card_templates.json",
    ]

    @classmethod
    def _find_config_path(cls, filename: str) -> Optional[str]:
        """Resolves absolute path of configuration file across environment directories."""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        candidates = [
            os.path.join(base_dir, "..", "..", "config", "templates", "xai", filename),
            os.path.join(base_dir, "..", "config", "templates", "xai", filename),
            os.path.join(os.getcwd(), "config", "templates", "xai", filename),
            os.path.join(base_dir, "..", "..", "config", filename),
            os.path.join(base_dir, "..", "config", filename),
            os.path.join(os.getcwd(), "config", filename),
        ]
        for p in candidates:
            if os.path.isfile(p):
                return p
        return None

    @classmethod
    def _read_json_file(cls, filename: str) -> Dict[str, Any]:
        """Reads and parses a single JSON configuration file safely."""
        path = cls._find_config_path(filename)
        if not path:
            logging.debug(f"[XaiTemplateRepository] File not found: {filename}")
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"[XaiTemplateRepository] Failed reading {filename}: {e}")
            return {}

    @classmethod
    def load_all_templates(cls, force_reload: bool = False) -> Dict[str, Any]:
        """
        Loads and aggregates all modular XAI JSON template files into a unified dictionary.
        Returns a dictionary keyed by language code (e.g., 'pt_br', 'en', 'es', 'fr', 'ru', 'zh').
        """
        if cls._cached_templates is not None and not force_reload:
            return cls._cached_templates

        merged: Dict[str, Any] = {}
        for filename in cls.CONFIG_FILES:
            data = cls._read_json_file(filename)
            for key, val in data.items():
                if key in ("subscript_rules", "document_layout"):
                    merged[key] = val
                elif isinstance(val, dict):
                    if key not in merged:
                        merged[key] = {}
                    if filename == "xai_categories.json":
                        merged[key]["categories"] = val
                    else:
                        merged[key].update(val)

        # Fallback to legacy single file if modular files are not found
        if not merged or len(merged.keys()) <= 1:
            legacy_data = cls._read_json_file("xai_report_templates.json")
            if legacy_data:
                merged = legacy_data

        cls._cached_templates = merged
        return merged

    @classmethod
    def load_categories(cls, language: Optional[str] = None, force_reload: bool = False) -> Dict[str, Any]:
        """Loads sensor category definitions directly from xai_categories.json."""
        if cls._cached_categories is None or force_reload:
            cls._cached_categories = cls._read_json_file("xai_categories.json")

        data = cls._cached_categories or {}
        if language:
            lang_key = language.lower().replace("-", "_")
            return data.get(lang_key, data.get("pt_br", {}))
        return data

    @classmethod
    def get_templates_for_language(cls, language: str = "pt_br") -> Dict[str, Any]:
        """Retrieves aggregated templates dictionary for specific language."""
        all_templates = cls.load_all_templates()
        lang_key = language.lower().replace("-", "_")
        lang_tmpl = all_templates.get(lang_key, all_templates.get("pt_br", {}))

        # Ensure categories sub-dict is included if present
        if "categories" not in lang_tmpl and lang_key in all_templates.get("categories", {}):
            lang_tmpl["categories"] = all_templates["categories"][lang_key]

        # Ensure document_layout is included
        if "document_layout" in all_templates and "document_layout" not in lang_tmpl:
            lang_tmpl["document_layout"] = all_templates["document_layout"]

        return lang_tmpl
