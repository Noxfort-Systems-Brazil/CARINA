# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Any, Dict, Optional

from utils.locale_manager_backend import LocaleManagerBackend
from xai.report_annex_cards_renderer import ReportAnnexCardsRenderer
from xai.report_block_base import ReportBlockBase
from xai.report_consolidated_summary_renderer import ReportConsolidatedSummaryRenderer
from xai.report_equations_renderer import ReportEquationsRenderer
from xai.report_executive_summary_renderer import ReportExecutiveSummaryRenderer
from xai.report_guardian_table_renderer import ReportGuardianTableRenderer
from xai.report_text_section_renderer import ReportTextSectionRenderer


class ReportBlockRegistry:
    """
    Registry for dynamic mapping and instantiation of report block renderers.
    Satisfies Open-Closed Principle (OCP) by allowing new block renderers to be registered
    without modifying existing builder logic.
    """

    def __init__(self) -> None:
        self._renderers: Dict[str, ReportBlockBase] = {}

    def register(self, block_type: str, renderer: ReportBlockBase) -> None:
        """Registers a renderer instance for a specific block type."""
        self._renderers[block_type] = renderer

    def get(self, block_type: str) -> Optional[ReportBlockBase]:
        """Retrieves registered renderer for a given block type."""
        return self._renderers.get(block_type)

    @classmethod
    def create_default(
        cls, templates: Dict[str, Any], locale_manager: Optional[LocaleManagerBackend] = None
    ) -> "ReportBlockRegistry":
        """Factory method to instantiate and populate registry with standard CARINA XAI renderers."""
        registry = cls()
        registry.register("executive_summary", ReportExecutiveSummaryRenderer(templates, locale_manager))
        registry.register("section", ReportTextSectionRenderer(templates, locale_manager))
        registry.register("equations_block", ReportEquationsRenderer(templates, locale_manager))
        registry.register("guardian_table", ReportGuardianTableRenderer(templates, locale_manager))
        registry.register("consolidated_summary", ReportConsolidatedSummaryRenderer(templates, locale_manager))
        registry.register("annex_cards", ReportAnnexCardsRenderer(templates, locale_manager))
        return registry
