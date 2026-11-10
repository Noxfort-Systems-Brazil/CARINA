# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later
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
                    logging.warning(f"[MFD_TEMPLATE_REPOSITORY] Failed to load JSON '{json_path}': {e}", exc_info=True)

        cls._templates_cache = unified_cache
        return cls._templates_cache
