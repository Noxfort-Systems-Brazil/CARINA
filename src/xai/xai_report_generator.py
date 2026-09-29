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

# File: src/xai/xai_report_generator.py
# Author: Gabriel Moraes
# Date: August 14, 2026

import json
import logging
import os
from typing import Any, Dict, Optional

from blocks.report_post_processor import ReportPostProcessor
from utils.locale_manager_backend import LocaleManagerBackend
from xai.agent_reconstructor import AgentReconstructor
from xai.captum_analyzer import CaptumAnalyzer
from xai.multi_agent_report_builder import MultiAgentReportBuilder
from xai.network_attribution_aggregator import NetworkAttributionAggregator
from xai.xai_agent_repository import XaiAgentRepository


class XaiReportGenerator:
    """
    Facade / Orchestrator for multi-agent XAI audit report generation.
    Coordinates agent repository discovery, Captum attributions, mathematical aggregation,
    chart rendering, and ABNT report assembly following the Single Responsibility Principle.
    """

    def __init__(
        self,
        scenario_results_dir: str,
        locale_manager: Optional[LocaleManagerBackend] = None,
        repository: Optional[XaiAgentRepository] = None,
        aggregator: Optional[NetworkAttributionAggregator] = None,
        report_builder: Optional[MultiAgentReportBuilder] = None,
    ) -> None:
        self.scenario_results_dir = scenario_results_dir
        self.locale_manager = locale_manager if locale_manager is not None else LocaleManagerBackend()
        self.checkpoints_dir = os.path.join(scenario_results_dir, "checkpoints")
        self.reconstructor = AgentReconstructor(self.checkpoints_dir) if os.path.exists(self.checkpoints_dir) else None

        # Inject or initialize single-responsibility sub-components
        self.repository = (
            repository if repository is not None else XaiAgentRepository(scenario_results_dir, self.locale_manager)
        )
        self.aggregator = (
            aggregator
            if aggregator is not None
            else NetworkAttributionAggregator(scenario_results_dir, self.locale_manager)
        )

        templates = self._load_templates()
        self.report_builder = (
            report_builder if report_builder is not None else MultiAgentReportBuilder(templates, self.locale_manager)
        )

    def _load_templates(self) -> Dict[str, Any]:
        """Loads localized report templates via XaiTemplateRepository."""
        from xai.xai_template_repository import XaiTemplateRepository

        lang = self.locale_manager.get_language()
        return XaiTemplateRepository.get_templates_for_language(lang)

    def generate_full_multi_agent_report(self, primary_agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Orchestrates end-to-end multi-agent XAI audit report generation."""
        logging.info(
            f"[XaiReportGenerator] Starting multi-agent XAI report orchestrator for {self.scenario_results_dir}..."
        )

        # 1. Discover audited agent IDs via Repository
        agent_ids = self.repository.discover_audited_agent_ids(primary_agent_id)

        # 2. Execute Captum mathematical attributions per agent in memory
        analyses_by_agent: Dict[str, Any] = {}
        primary_image_base64 = None

        for aid in agent_ids:
            try:
                agent = self.reconstructor.reconstruct_agent(aid) if self.reconstructor else None
                if not agent:
                    continue
                analyzer = CaptumAnalyzer(
                    agent=agent, scenario_results_dir=self.scenario_results_dir, locale_manager=self.locale_manager
                )
                res = analyzer.generate_analysis_in_memory()
                if res:
                    analyses_by_agent[aid] = res
                    if primary_agent_id and aid == primary_agent_id:
                        primary_image_base64 = res.get("image_base64")
            except Exception as e:
                logging.warning(f"[XaiReportGenerator] Captum analysis failed for agent {aid}: {e}")

        # 3. Compute network-wide aggregated feature importances and general chart
        aggregation_res = self.aggregator.aggregate_network_analysis(analyses_by_agent)
        global_image_base64 = aggregation_res.get("global_image_base64")

        is_all = not primary_agent_id or str(primary_agent_id).upper() in ["ALL", "ALL_AGENTS", "TODOS"]
        if is_all or not primary_image_base64:
            primary_image_base64 = global_image_base64 or primary_image_base64

        # 4. Assemble ABNT Markdown report text via ReportBuilder
        markdown_text = self.report_builder.build_markdown(
            agent_ids, analyses_by_agent, global_image_base64=global_image_base64
        )
        cleaned_text = ReportPostProcessor.enforce_semantic_consistency(markdown_text)

        return {"status": "complete", "image_base64": primary_image_base64, "text_content": cleaned_text}
