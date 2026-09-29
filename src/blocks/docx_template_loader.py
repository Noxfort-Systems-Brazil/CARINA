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

# File: src/blocks/docx_template_loader.py
# Author: Gabriel Moraes
# Date: September 2026

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
                    logging.warning(f"[DocxTemplateLoader] Failed to load OMML templates from '{json_path}': {e}")

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
                    logging.warning(f"[DocxTemplateLoader] Failed to load subscript rules from '{json_path}': {e}")

        _cached_subscript_config = {
            "subscript_regex_pattern": (
                r"([a-zA-Zα-ωΑ-Ω\u0370-\u03ff\u1f00-\u1ffe\']+|"
                r"\b[a-zA-Zα-ωΑ-Ω\u0370-\u03ff\u1f00-\u1ffe]{1,50})_\{?([a-zA-Z0-9α-ωΑ-Ω\u0370-\u03ff\u1f00-\u1ffe]+)\}?|"
                r"\b(v)(real|limite)\b|\b(F)(ideal)\b|\b(P)(95)\b"
            )
        }
        return _cached_subscript_config
