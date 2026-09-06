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

# File: src/xai/report_block_registry.py
# Author: Gabriel Moraes
# Date: August 14, 2026

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
