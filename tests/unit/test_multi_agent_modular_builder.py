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

# File: tests/unit/test_multi_agent_modular_builder.py
# Author: Gabriel Moraes
# Date: August 14, 2026

from unittest.mock import MagicMock

import pytest

from xai.multi_agent_report_builder import MultiAgentReportBuilder
from xai.report_annex_cards_renderer import ReportAnnexCardsRenderer
from xai.report_block_base import ReportBlockBase
from xai.report_block_registry import ReportBlockRegistry
from xai.report_consolidated_summary_renderer import ReportConsolidatedSummaryRenderer
from xai.report_data_collector import ReportDataCollector
from xai.report_equations_renderer import ReportEquationsRenderer
from xai.report_guardian_table_renderer import ReportGuardianTableRenderer
from xai.report_metrics_transformer import ReportMetricsTransformer
from xai.report_text_section_renderer import ReportTextSectionRenderer


def test_report_block_registry_operations():
    registry = ReportBlockRegistry()
    dummy_renderer = MagicMock(spec=ReportBlockBase)

    assert registry.get("custom_block") is None
    registry.register("custom_block", dummy_renderer)
    assert registry.get("custom_block") is dummy_renderer


def test_report_block_registry_default_factory():
    templates = {"title": "Test Title"}
    registry = ReportBlockRegistry.create_default(templates)

    assert isinstance(registry.get("section"), ReportTextSectionRenderer)
    assert isinstance(registry.get("equations_block"), ReportEquationsRenderer)
    assert isinstance(registry.get("guardian_table"), ReportGuardianTableRenderer)
    assert isinstance(registry.get("consolidated_summary"), ReportConsolidatedSummaryRenderer)
    assert isinstance(registry.get("annex_cards"), ReportAnnexCardsRenderer)


def test_report_metrics_transformer():
    analyses = {
        "agent_1": {
            "has_tensor_data": True,
            "sorted_analysis": [
                {"name": "Flow Rate", "importance": 0.4, "description": "Traffic flow"},
                {"name": "Queue Length", "importance": 0.6, "description": "Waiting queue"},
            ],
            "image_base64": "dummy_b64_1",
        },
        "agent_2": {"has_tensor_data": False, "sorted_analysis": []},
    }

    transformed = ReportMetricsTransformer.transform_agent_metrics(analyses)

    assert transformed["agent_1"]["has_data"] is True
    assert len(transformed["agent_1"]["items"]) == 2
    # Total sum is 1.0 -> Queue Length is 60.0%, Flow Rate is 40.0%
    assert transformed["agent_1"]["top_3"][0]["name"] == "Queue Length"
    assert transformed["agent_1"]["top_3"][0]["pct_str"] == "60,0%"
    assert transformed["agent_1"]["image_base64"] == "dummy_b64_1"

    assert transformed["agent_2"]["has_data"] is False
    assert transformed["agent_2"]["items"] == []


def test_report_data_collector_with_mock_repo():
    mock_repo = MagicMock()
    mock_repo.get_guardian_veto_statistics.return_value = {
        "total_evaluated": 150,
        "total_approved": 145,
        "temporal_interventions": 3,
        "critical_vetoes": 2,
        "compliance_rate": 96.666,
        "top_veto_reason": "Excessive queue",
    }

    collector = ReportDataCollector(step_repo=mock_repo)
    stats = collector.collect_guardian_statistics(["agent_1"])

    assert "agent_1" in stats
    assert stats["agent_1"]["eval_count"] == 150
    assert stats["agent_1"]["approved_count"] == 145
    assert stats["agent_1"]["rate_str"] == "96,7%"
    assert stats["agent_1"]["reason"] == "Excessive queue"


def test_report_data_collector_fallback():
    collector = ReportDataCollector(step_repo=None)
    stats = collector.collect_guardian_statistics(["agent_missing"])

    assert "agent_missing" in stats
    assert stats["agent_missing"]["eval_count"] == 0
    assert stats["agent_missing"]["rate_str"] == "100,0%"
    assert stats["agent_missing"]["reason"] == "Aguardando Amostragem"


def test_renderers_individual_rendering():
    templates = {
        "sec_title": "### Section Title",
        "sec_body": "Narrative with {total_agents} agents.",
        "eq_title": "#### Formal Model",
        "eq_intro": "Mathematical formulation:",
        "eq_f": "$$ y = f(x) $$",
        "eq_p": "Where x is input.",
        "eq_ax": "Axiom of Completeness",
        "eq_cf": "$$ \sum x_i = y $$",
        "eq_cd": "Completeness satisfied.",
        "g_title": "### Guardian Table",
        "g_desc": "Audit results",
        "sum_title": "### Summary",
        "sum_desc": "Global analysis",
        "annex_title": "### Annex I",
        "annex_desc": "Per-agent sheets",
    }

    context = {
        "agent_ids": ["A1"],
        "analyses": {
            "A1": {
                "has_tensor_data": True,
                "sorted_analysis": [{"name": "Sensor_1", "importance": 1.0, "description": "Desc"}],
                "image_base64": "img123",
            }
        },
        "global_image_base64": "global123",
        "guardian_stats": {
            "A1": {
                "eval_count": 10,
                "approved_count": 10,
                "temporal_count": 0,
                "critical_count": 0,
                "rate_str": "100,0%",
                "approved_pct": "100,0",
                "reason": "OK",
            }
        },
        "metrics_by_agent": ReportMetricsTransformer.transform_agent_metrics(
            {
                "A1": {
                    "has_tensor_data": True,
                    "sorted_analysis": [{"name": "Sensor_1", "importance": 1.0, "description": "Desc"}],
                    "image_base64": "img123",
                }
            }
        ),
    }

    # Test Text Section Renderer
    lines = []
    text_renderer = ReportTextSectionRenderer(templates)
    text_renderer.render(lines, {"title_key": "sec_title", "content_keys": ["sec_body"]}, context)
    assert "### Section Title" in lines
    assert "Narrative with 1 agents." in lines

    # Test Equations Renderer
    lines = []
    eq_renderer = ReportEquationsRenderer(templates)
    eq_renderer.render(
        lines,
        {
            "title_key": "eq_title",
            "intro_key": "eq_intro",
            "equations": [
                {
                    "title_key": "eq_title",
                    "desc_key": "eq_intro",
                    "formula_key": "eq_f",
                    "params_key": "eq_p",
                    "completeness_axiom_key": "eq_ax",
                    "completeness_formula_key": "eq_cf",
                    "completeness_desc_key": "eq_cd",
                }
            ],
        },
        context,
    )
    assert "$$ y = f(x) $$" in lines
    assert "$$ \sum x_i = y $$" in lines

    # Test Guardian Table Renderer
    lines = []
    g_renderer = ReportGuardianTableRenderer(templates)
    g_renderer.render(lines, {"title_key": "g_title", "desc_key": "g_desc"}, context)
    assert any("Cruzamento ID A1" in l for l in lines)

    # Test Consolidated Summary Renderer
    lines = []
    sum_renderer = ReportConsolidatedSummaryRenderer(templates)
    sum_renderer.render(lines, {"title_key": "sum_title", "desc_key": "sum_desc"}, context)
    assert any("global123" in l for l in lines)

    # Test Annex Cards Renderer - Single agent mode (chart not duplicated in Annex I)
    lines = []
    annex_renderer = ReportAnnexCardsRenderer(templates)
    annex_renderer.render(lines, {"title_key": "annex_title", "desc_key": "annex_desc"}, context)
    assert not any("img123" in l for l in lines)

    # Test Annex Cards Renderer - Multi agent mode (charts rendered per intersection)
    multi_context = dict(context)
    multi_context["agent_ids"] = ["A1", "A2"]
    multi_context["metrics_by_agent"] = ReportMetricsTransformer.transform_agent_metrics(
        {
            "A1": {
                "has_tensor_data": True,
                "sorted_analysis": [{"name": "Sensor_1", "importance": 1.0, "description": "Desc"}],
                "image_base64": "img123",
            },
            "A2": {
                "has_tensor_data": True,
                "sorted_analysis": [{"name": "Sensor_2", "importance": 1.0, "description": "Desc"}],
                "image_base64": "img456",
            },
        }
    )
    lines_multi = []
    annex_renderer.render(lines_multi, {"title_key": "annex_title", "desc_key": "annex_desc"}, multi_context)
    assert any("img123" in l for l in lines_multi)
    assert any("img456" in l for l in lines_multi)


def test_multi_agent_report_builder_end_to_end():
    templates = {
        "section1_title": "# Relatório Pericial XAI",
        "section1_intro1": "Auditoria de {total_agents} cruzamentos.",
        "guardian_section_title": "### Conformidade Guardião",
        "guardian_table_header": "| ID | Avaliações | Taxa |\n| :--- | :---: | :---: |",
        "guardian_table_row": "| {c_label} | {eval_count} | {rate_str} |",
        "agent_label": "Cruzamento {aid}",
        "document_layout": [
            {"id": "intro", "type": "section", "title_key": "section1_title", "content_keys": ["section1_intro1"]},
            {
                "id": "guardian",
                "type": "guardian_table",
                "title_key": "guardian_section_title",
                "header_template": "guardian_table_header",
                "row_template": "guardian_table_row",
            },
        ],
    }

    builder = MultiAgentReportBuilder(templates=templates)
    md = builder.build_markdown(agent_ids=["J1", "J2"], analyses={})

    assert "# Relatório Pericial XAI" in md
    assert "Auditoria de 2 cruzamentos." in md
    assert "### Conformidade Guardião" in md
    assert "Cruzamento J1" in md
    assert "Cruzamento J2" in md
