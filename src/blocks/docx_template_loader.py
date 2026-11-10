# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import logging
import os
from typing import Any, Dict, Optional

_cached_omml_config: Optional[Dict[str, Any]] = None
_cached_subscript_config: Optional[Dict[str, Any]] = None


class DocxTemplateLoader:
    """Dynamically loads and caches OMML equations and subscript configurations from JSON templates."""

    @classmethod
    def load_omml_templates(cls) -> Dict[str, Any]:
        """Loads OMML equation XML templates with in-memory caching."""
        global _cached_omml_config
        if _cached_omml_config is not None:
            return _cached_omml_config

        base_dir = os.path.dirname(os.path.abspath(__file__))
        candidates = [
            os.path.join(base_dir, "..", "..", "config", "templates", "omml_equation_templates.json"),
            os.path.join(base_dir, "..", "config", "templates", "omml_equation_templates.json"),
            os.path.join(os.getcwd(), "config", "templates", "omml_equation_templates.json"),
            os.path.join(base_dir, "..", "..", "config", "omml_equation_templates.json"),
            os.path.join(base_dir, "..", "config", "omml_equation_templates.json"),
            os.path.join(os.getcwd(), "config", "omml_equation_templates.json"),
        ]

        for json_path in candidates:
            if os.path.exists(json_path):
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        _cached_omml_config = json.load(f)
                        return _cached_omml_config
                except Exception as e:
                    logging.warning(f"[DocxTemplateLoader] Failed to load OMML templates from '{json_path}': {e}", exc_info=True)

        _cached_omml_config = {
            "namespaces": (
                'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" '
                'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
            ),
            "templates": {},
        }
        return _cached_omml_config

    @classmethod
    def load_subscript_rules(cls) -> Dict[str, Any]:
        """Loads subscript regex rules from template configurations with in-memory caching."""
        global _cached_subscript_config
        if _cached_subscript_config is not None:
            return _cached_subscript_config

        base_dir = os.path.dirname(os.path.abspath(__file__))
        candidates = [
            os.path.join(base_dir, "..", "..", "config", "templates", "xai", "xai_report_sections.json"),
            os.path.join(base_dir, "..", "config", "templates", "xai", "xai_report_sections.json"),
            os.path.join(os.getcwd(), "config", "templates", "xai", "xai_report_sections.json"),
            os.path.join(base_dir, "..", "..", "config", "xai_report_sections.json"),
            os.path.join(base_dir, "..", "config", "xai_report_sections.json"),
            os.path.join(os.getcwd(), "config", "xai_report_sections.json"),
            os.path.join(base_dir, "..", "..", "config", "xai_report_templates.json"),
            os.path.join(base_dir, "..", "config", "xai_report_templates.json"),
            os.path.join(os.getcwd(), "config", "xai_report_templates.json"),
            os.path.join(os.getcwd(), "config", "report_templates.json"),
        ]

        for json_path in candidates:
            if os.path.exists(json_path):
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                        if "subscript_rules" in cfg:
                            _cached_subscript_config = cfg["subscript_rules"]
                            return _cached_subscript_config
                except Exception as e:
                    logging.warning(f"[DocxTemplateLoader] Failed to load subscript rules from '{json_path}': {e}", exc_info=True)

        _cached_subscript_config = {
            "subscript_regex_pattern": (
                r"([a-zA-Zα-ωΑ-Ω\u0370-\u03ff\u1f00-\u1ffe\']+|"
                r"\b[a-zA-Zα-ωΑ-Ω\u0370-\u03ff\u1f00-\u1ffe]{1,50})_\{?([a-zA-Z0-9α-ωΑ-Ω\u0370-\u03ff\u1f00-\u1ffe]+)\}?|"
                r"\b(v)(real|limite)\b|\b(F)(ideal)\b|\b(P)(95)\b"
            )
        }
        return _cached_subscript_config
