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

# File: src/xai/multi_agent_report_builder.py
# Author: Gabriel Moraes
# Date: August 14, 2026

import logging
from typing import Any, Dict, List, Optional

from utils.locale_manager_backend import LocaleManagerBackend
from xai.report_block_registry import ReportBlockRegistry
from xai.report_data_collector import ReportDataCollector
from xai.report_metrics_transformer import ReportMetricsTransformer


class MultiAgentReportBuilder:
    """
    Pure orchestrator for ABNT NBR 14724 multi-agent XAI audit reports.
    Satisfies Single Responsibility (SRP), Open-Closed (OCP), and Dependency Inversion (DIP)
    principles by delegating layout block rendering to a pluggable registry,
    data persistence queries to a collector, and mathematical normalizations to a metrics transformer.
    """

    def __init__(
        self,
        templates: Dict[str, Any],
        locale_manager: Optional[LocaleManagerBackend] = None,
        registry: Optional[ReportBlockRegistry] = None,
        data_collector: Optional[ReportDataCollector] = None,
        metrics_transformer: Optional[ReportMetricsTransformer] = None,
    ) -> None:
        self.templates = templates
        self.locale_manager = locale_manager if locale_manager is not None else LocaleManagerBackend()
        self.registry = (
            registry
            if registry is not None
            else ReportBlockRegistry.create_default(self.templates, self.locale_manager)
        )
        self.data_collector = data_collector if data_collector is not None else ReportDataCollector(self.locale_manager)
        self.metrics_transformer = (
            metrics_transformer if metrics_transformer is not None else ReportMetricsTransformer()
        )

    def _t(self, key: str, default: str = "", **kwargs) -> str:
        """Helper to resolve localized string templates."""
        tmpl = self.templates.get(key, default)
        if kwargs and tmpl:
            try:
                return tmpl.format(**kwargs)
            except Exception:
                return tmpl
        return tmpl

    def build_markdown(
        self, agent_ids: List[str], analyses: Dict[str, Any], global_image_base64: Optional[str] = None
    ) -> str:
        """
        Orchestrates end-to-end assembly of technical ABNT report Markdown dynamically
        from document_layout configuration blocks.
        """
        lines: List[str] = []

        # 1. Collect required persistence and safety compliance statistics
        default_reason = self._t("table_missing_data_factor", "Aguardando Amostragem")
        guardian_stats = self.data_collector.collect_guardian_statistics(
            agent_ids=agent_ids, default_reason_text=default_reason
        )

        # 2. Transform and normalize neural tensor feature attributions
        metrics_by_agent = self.metrics_transformer.transform_agent_metrics(analyses)

        # 3. Assemble unified execution context for block renderers
        context: Dict[str, Any] = {
            "agent_ids": agent_ids,
            "analyses": analyses,
            "global_image_base64": global_image_base64,
            "guardian_stats": guardian_stats,
            "metrics_by_agent": metrics_by_agent,
        }

        # 4. Dispatch layout blocks to registered modular renderers
        layout = self.templates.get("document_layout", self._get_default_layout())

        for block in layout:
            b_type = block.get("type", "")
            renderer = self.registry.get(b_type)
            if renderer:
                renderer.render(lines, block, context)
            else:
                logging.warning(f"[MultiAgentReportBuilder] No registered renderer found for block type '{b_type}'")

        return "\n".join(lines)

    def _get_default_layout(self) -> List[Dict[str, Any]]:
        """Fallback default layout schema if document_layout is absent in JSON."""
        return [
            {
                "id": "part1_executive_summary",
                "type": "executive_summary",
                "title_key": "exec_part_title",
                "obj_title_key": "exec_obj_title",
                "obj_desc_key": "exec_obj_desc",
                "highlights_title_key": "exec_highlights_title",
                "highlights_desc_key": "exec_highlights_desc",
                "table_title_key": "exec_table_title",
                "header_template": "executive_table_header",
                "row_template": "executive_table_row",
            },
            {
                "id": "part2_technical_intro",
                "type": "section",
                "title_key": "part2_tech_title",
                "content_keys": ["section1_intro1", "section1_intro2"],
            },
            {
                "id": "section2_equations",
                "type": "equations_block",
                "title_key": "section2_title",
                "intro_key": "section2_intro",
                "equations": [
                    {
                        "title_key": "eq1_title",
                        "desc_key": "eq1_desc",
                        "formula_key": "eq1_formula",
                        "params_key": "eq1_params",
                    },
                    {
                        "title_key": "eq2_title",
                        "desc_key": "eq2_desc",
                        "formula_key": "eq2_formula",
                        "params_key": "eq2_params",
                    },
                    {
                        "title_key": "eq3_title",
                        "desc_key": "eq3_desc",
                        "formula_key": "eq3_formula",
                        "params_key": "eq3_params",
                    },
                    {
                        "title_key": "eq4_title",
                        "desc_key": "eq4_desc",
                        "formula_key": "eq4_formula",
                        "params_key": "eq4_params",
                    },
                    {
                        "title_key": "eq5_pae_title",
                        "desc_key": "eq5_pae_desc",
                        "formula_key": "eq5_pae_formula",
                        "params_key": "eq5_pae_params",
                    },
                    {
                        "title_key": "eq5_title",
                        "desc_key": "equation_method",
                        "formula_key": "equation_formula",
                        "params_key": "equation_variables",
                        "completeness_axiom_key": "completeness_axiom",
                        "completeness_formula_key": "completeness_formula",
                        "completeness_desc_key": "completeness_desc",
                    },
                ],
            },
            {"id": "section3_tcn", "type": "section", "title_key": "section3_title", "content_keys": ["section3_tcn"]},
            {
                "id": "section4_guardian_table",
                "type": "guardian_table",
                "title_key": "guardian_section_title",
                "desc_key": "guardian_section_desc",
                "header_template": "guardian_table_header",
                "row_template": "guardian_table_row",
            },
            {
                "id": "section5_pae",
                "type": "section",
                "title_key": "pae_section_title",
                "content_keys": ["pae_section_desc"],
            },
            {
                "id": "section6_consolidated",
                "type": "consolidated_summary",
                "title_key": "section4_title",
                "desc_key": "section4_desc",
                "chart_caption": "global_chart_caption",
                "item_template": "consolidated_item",
            },
            {
                "id": "anexo1_cards",
                "type": "annex_cards",
                "title_key": "anexo_title",
                "desc_key": "anexo_desc",
                "card_header": "agent_card_header",
                "card_intro": "agent_card_intro",
                "card_item": "agent_card_item",
                "card_missing_data": "agent_card_missing_data",
                "guardian_card_audit": "guardian_card_audit",
                "pae_card_audit": "pae_card_audit",
                "agent_card_opinion": "agent_card_opinion",
                "agent_card_chart_caption": "agent_card_chart_caption",
            },
            {
                "id": "section7_directives",
                "type": "section",
                "title_key": "section5_title",
                "content_keys": ["section5_guidelines"],
            },
            {
                "id": "section8_final",
                "type": "section",
                "title_key": "section6_title",
                "content_keys": ["section6_desc"],
            },
        ]
