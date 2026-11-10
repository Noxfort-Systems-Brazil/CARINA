# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later
from typing import Any, Dict, List

from mfd.mfd_audit_sheet_formatter import MFDAuditSheetFormatter
from mfd.mfd_justification_resolver import MFDJustificationResolver
from mfd.mfd_table_formatter import MFDTableFormatter
from mfd.mfd_template_repository import MFDTemplateRepository


class MFDTemplateProvider:
    """
    Responsibility (Facade Pattern & OCP): Serves as a unified facade for accessing MFD report templates,
    delegating responsibilities to specialized classes and reading document section arrays dynamically from JSON.
    - MFDTemplateRepository: JSON loading and caching
    - MFDTableFormatter: Tables (Section 3) and Consolidated Summaries (Section 4)
    - MFDJustificationResolver: Deterministic technical justifications
    - MFDAuditSheetFormatter: Anexo I Audit Sheets
    Provides 100% backwards compatibility.
    """

    @classmethod
    def get_section_4_equations(cls, lang: str = "pt_br") -> str:
        """
        Returns Section 2: MFD Mathematical Equations & Método DA SILVA Maturation Curriculum with 3 Criteria
        dynamically rendered from JSON lines array.

        :param lang: UI target language code
        :return: Formatted Section 2 Markdown string
        """
        raw_cfg = MFDTemplateRepository.load_templates().get("section_2_equations", {})
        lang_key = (lang or "pt_br").lower()
        cfg = raw_cfg.get(lang_key, raw_cfg.get("pt_br", raw_cfg.get("en", {})))

        lines = cfg.get("lines", [])
        return "\n".join(lines)

    @classmethod
    def get_section_5_synthesis_table(cls, intersections_list: List[Dict[str, Any]], lang: str = "pt_br") -> str:
        """Delegates Section 3 table formatting to MFDTableFormatter."""
        return MFDTableFormatter.get_section_5_synthesis_table(intersections_list, lang=lang)

    @classmethod
    def get_section_6_consolidated_summary(cls, normalized_data: Dict[str, Any], lang: str = "pt_br") -> str:
        """Delegates Section 4 summary formatting to MFDTableFormatter."""
        return MFDTableFormatter.get_section_6_consolidated_summary(normalized_data, lang=lang)

    @classmethod
    def generate_deterministic_justification(cls, row: Dict[str, Any], lang: str = "pt_br") -> str:
        """Delegates technical justification resolution to MFDJustificationResolver."""
        return MFDJustificationResolver.generate_deterministic_justification(row, lang=lang)

    @classmethod
    def get_intersection_audit_sheet_template(
        cls, row: Dict[str, Any], justification: str = None, lang: str = "pt_br"
    ) -> str:
        """Delegates Anexo I Audit Sheet formatting to MFDAuditSheetFormatter."""
        return MFDAuditSheetFormatter.get_intersection_audit_sheet_template(row, justification=justification, lang=lang)

    @classmethod
    def get_intersection_ficha_template(
        cls, row: Dict[str, Any], justificativa: str = None, lang: str = "pt_br"
    ) -> str:
        """Backwards-compatible alias for get_intersection_audit_sheet_template."""
        return cls.get_intersection_audit_sheet_template(row, justification=justificativa, lang=lang)
