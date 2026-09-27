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

# File: src/mfd/mfd_template_repository.py
# Author: Gabriel Moraes
# Date: August 12, 2026

import json
import logging
import os
from typing import Any, Dict, List


class MFDTemplateRepository:
    """
    Responsibility (SRP & DIP): Handles file I/O operations for reading modular MFD report templates
    (mfd_report_sections.json, mfd_table_templates.json, mfd_summary_directives.json, mfd_audit_sheet_templates.json)
    from config/templates/mfd/ and managing memory caching with 100% backwards compatibility.
    Follows SOLID principles.
    """

    _templates_cache: Dict[str, Any] = None

    _MODULAR_CONFIG_FILES: List[str] = [
        "mfd_report_sections.json",
        "mfd_table_templates.json",
        "mfd_summary_directives.json",
        "mfd_audit_sheet_templates.json",
    ]

    @classmethod
    def load_templates(cls) -> Dict[str, Any]:
        """
        Loads report templates from specialized JSON files in config/templates/mfd/ with caching.

        :return: Unified dictionary containing parsed JSON template configurations
        """
        if cls._templates_cache is not None:
            return cls._templates_cache

        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        unified_cache: Dict[str, Any] = {}

        for config_filename in cls._MODULAR_CONFIG_FILES:
            candidates = [
                os.path.join(base_dir, "config", "templates", "mfd", config_filename),
                os.path.join(base_dir, "config", config_filename),
            ]
            json_path = None
            for p in candidates:
                if os.path.exists(p):
                    json_path = p
                    break

            if json_path:
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        file_content = json.load(f)
                        if isinstance(file_content, dict):
                            unified_cache.update(file_content)
                            logging.info(f"[MFD_TEMPLATE_REPOSITORY] Loaded modular template file: {json_path}")
                except Exception as e:
                    logging.warning(f"[MFD_TEMPLATE_REPOSITORY] Failed to load JSON '{json_path}': {e}")

        cls._templates_cache = unified_cache
        return cls._templates_cache
