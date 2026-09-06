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

# File: tests/unit/test_xai_report_builder.py
# Author: Gabriel Moraes
# Date: 2026-06-19

import os

import pytest

from blocks.structured_report_builder import StructuredReportBuilder as XaiStructuredReportBuilder


def test_xai_structured_report_builder_generation(tmp_path):
    # Setup destinations
    output_docx = os.path.join(tmp_path, "test_report.docx")

    # Mock configurations
    config = {
        "logo_path": "",
        "secretary_name": "Dr. Test Secretary",
        "secretary_title": "Director of Test Automation",
        "agency_name": "Test Authority Group",
        "department_name": "Quality Assurance Bureau",
        "title": "LAUDO AUTOMÁTICO DE TESTES UNITÁRIOS",
        "font_name": "Times New Roman",
        "font_size": 12,
        "margin_top": 1.25,
        "margin_bottom": 1.25,
        "margin_left": 1.25,
        "margin_right": 1.25,
        "line_spacing": 1.5,
        "alignment": "left",
    }

    # Mock contexts
    context = {
        "agent_id": "intersection_123",
        "scenario": "test_scenario_suite",
        "engine_version": "CARINA TestEngine v1.0.0",
        "image_path": "",
        "text_content": "### Parecer Técnico\nO agente priorizou o fluxo da avenida principal devido à detecção de longa fila no sensor 1.",
    }

    # Test all blocks
    builder = XaiStructuredReportBuilder()
    success = builder.generate_report(output_docx, context, config)

    assert success is True
    assert os.path.exists(output_docx)
    assert os.path.getsize(output_docx) > 0


def test_xai_structured_report_builder_custom_block_order(tmp_path):
    output_docx = os.path.join(tmp_path, "test_report_custom.docx")

    config = {"secretary_name": "Dr. Test Secretary", "title": "TITULO REORDENADO"}

    context = {"agent_id": "agent_456", "text_content": "Texto de teste"}

    # Generate report with custom block order
    builder = XaiStructuredReportBuilder(block_order=["title", "content", "signature"])
    success = builder.generate_report(output_docx, context, config)

    assert success is True
    assert os.path.exists(output_docx)
    assert os.path.getsize(output_docx) > 0


def test_mfd_structured_report_builder_generation(tmp_path):
    output_docx = os.path.join(tmp_path, "test_mfd_report.docx")

    config = {
        "logo_path": "",
        "secretary_name": "Secretário de Mobilidade",
        "secretary_title": "Titular",
        "agency_name": "Prefeitura",
        "department_name": "Trânsito",
        "title": "RELATÓRIO MFD DE TESTE",
        "mode": "MFD",
        "font_name": "Calibri",
        "font_size": 11,
        "margin_top": 2.0,
        "margin_bottom": 2.0,
        "margin_left": 2.0,
        "margin_right": 2.0,
        "line_spacing": 1.15,
        "alignment": "justify",
    }

    context = {
        "scenario": "mfd_scenario_test",
        "engine_version": "CARINA TestEngine v1.0.0",
        "image_path": "",
        "text_content": "## Visão Global da Malha Viária\n- **Desde a última análise:** velocidade passou de **38,1 km/h** para **40,2 km/h**.\n- **Desde o início da operação:** manteve-se estável.",
    }

    builder = XaiStructuredReportBuilder()
    success = builder.generate_report(output_docx, context, config)

    assert success is True
    assert os.path.exists(output_docx)
    assert os.path.getsize(output_docx) > 0


def test_report_exporter_fallback_planning(tmp_path):
    import base64
    from unittest.mock import MagicMock

    from ui.formatting.report_exporter import ReportExporter

    # Setup directories
    results_dir = os.path.join(tmp_path, "results")
    maps_dir = os.path.join(results_dir, "maps")
    os.makedirs(maps_dir, exist_ok=True)

    # Create a dummy image
    dummy_img_path = os.path.join(maps_dir, "map_planning.png")
    # A tiny valid 1x1 PNG file
    png_data = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    )
    with open(dummy_img_path, "wb") as f:
        f.write(png_data)

    output_docx = os.path.join(tmp_path, "exported_fallback_report.docx")
    mock_page = MagicMock()
    mock_locale_manager = MagicMock()
    mock_locale_manager.get_string.side_effect = lambda key, default=None, **kwargs: default

    # Call export_report with empty image_base64 to trigger fallback
    success = ReportExporter.export_report(
        page=mock_page,
        locale_manager=mock_locale_manager,
        save_path=output_docx,
        image_base64="",
        text_content="Test planning text content",
        results_dir=results_dir,
        mode="PLANNING",
        agent_id="test_agent",
    )

    assert success is True
    assert os.path.exists(output_docx)
    assert os.path.getsize(output_docx) > 0


def test_chart_block_build_fallback(tmp_path):
    import base64

    from docx import Document

    from blocks.chart import ChartBlock

    results_dir = os.path.join(tmp_path, "results")
    maps_dir = os.path.join(results_dir, "maps")
    os.makedirs(maps_dir, exist_ok=True)

    dummy_img_path = os.path.join(maps_dir, "map_planning.png")
    png_data = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    )
    with open(dummy_img_path, "wb") as f:
        f.write(png_data)

    doc = Document()
    context = {"image_path": "", "results_dir": results_dir}
    config = {"mode": "PLANNING", "chart_title": "Planning Map", "chart_caption": "Dummy Caption"}

    block = ChartBlock()
    # This should not raise an exception and should successfully fall back
    block.build(doc, context, config)

    # Let's verify something was written to the doc
    assert len(doc.paragraphs) > 0


def test_xai_executive_summary_renderer_rendering():
    from utils.locale_manager_backend import LocaleManagerBackend
    from xai.report_executive_summary_renderer import ReportExecutiveSummaryRenderer
    from xai.xai_template_repository import XaiTemplateRepository

    lm = LocaleManagerBackend()
    templates = XaiTemplateRepository.get_templates_for_language("pt_br")
    renderer = ReportExecutiveSummaryRenderer(templates, lm)

    lines = []
    block = {
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
    }
    context = {
        "agent_ids": ["1116667894", "1193472473"],
        "guardian_stats": {
            "1116667894": {
                "eval_count": 3435,
                "approved_count": 2306,
                "temporal_count": 1129,
                "critical_count": 0,
                "rate_str": "67,1%",
                "approved_pct": "67,1",
            },
            "1193472473": {
                "eval_count": 3435,
                "approved_count": 2000,
                "temporal_count": 1435,
                "critical_count": 0,
                "rate_str": "58,2%",
                "approved_pct": "58,2",
            },
        },
        "metrics_by_agent": {
            "1116667894": {
                "has_data": True,
                "top_3": [
                    {"name": "Coordenação Gráfica GATv2 Lite (Onda Verde)", "pct_str": "74,4%", "importance": 5.521},
                    {"name": "Velocidade Média de Escoamento (km/h)", "pct_str": "8,7%", "importance": 0.648},
                ],
            },
            "1193472473": {
                "has_data": True,
                "top_3": [
                    {"name": "Coordenação Gráfica GATv2 Lite (Onda Verde)", "pct_str": "72,4%", "importance": 5.665},
                    {"name": "Velocidade Média de Escoamento (km/h)", "pct_str": "9,5%", "importance": 0.743},
                ],
            },
        },
    }

    renderer.render(lines, block, context)
    rendered_text = "\n".join(lines)

    assert "PARTE I — SUMÁRIO EXECUTIVO" in rendered_text
    assert "Objetivo da Auditoria" in rendered_text
    assert "Quadro Sintético de Resultados por Cruzamento" in rendered_text
    assert "1116667894" in rendered_text
    assert "1193472473" in rendered_text
    assert "Homologado com Excelência" in rendered_text


def test_multi_agent_report_builder_with_dual_level_structure(tmp_path):
    from blocks.structured_report_builder import StructuredReportBuilder
    from utils.locale_manager_backend import LocaleManagerBackend
    from xai.multi_agent_report_builder import MultiAgentReportBuilder
    from xai.xai_template_repository import XaiTemplateRepository

    lm = LocaleManagerBackend()
    templates = XaiTemplateRepository.get_templates_for_language("pt_br")
    builder = MultiAgentReportBuilder(templates, lm)

    agent_ids = ["1116667894", "1193472473"]
    analyses = {
        "1116667894": {
            "has_tensor_data": True,
            "image_base64": "",
            "sorted_analysis": [
                {
                    "name": "Coordenação Gráfica GATv2 Lite (Onda Verde)",
                    "importance": 5.521,
                    "description": "Sincronismo",
                },
                {"name": "Velocidade Média de Escoamento (km/h)", "importance": 0.648, "description": "Velocidade"},
            ],
        },
        "1193472473": {
            "has_tensor_data": True,
            "image_base64": "",
            "sorted_analysis": [
                {
                    "name": "Coordenação Gráfica GATv2 Lite (Onda Verde)",
                    "importance": 5.665,
                    "description": "Sincronismo",
                },
                {"name": "Velocidade Média de Escoamento (km/h)", "importance": 0.743, "description": "Velocidade"},
            ],
        },
    }

    markdown = builder.build_markdown(agent_ids, analyses)

    assert "PARTE I — SUMÁRIO EXECUTIVO" in markdown
    assert "PARTE II — AUDITORIA PERICIAL" in markdown
    assert "PARTE III — FICHAS TÉCNICAS E PERICIAIS" in markdown
    assert "PARTE IV — DIRETRIZES TÉCNICAS" in markdown

    # Also test building docx from this markdown
    output_docx = os.path.join(tmp_path, "dual_level_xai_report.docx")
    docx_builder = StructuredReportBuilder()
    config = {
        "secretary_name": "Dr. Gabriel Moraes",
        "secretary_title": "Secretário de Mobilidade Urbana e Trânsito",
        "agency_name": "Prefeitura Municipal de Apucarana",
        "department_name": "Departamento de Mobilidade Inteligente",
        "ordinance_enabled": "true",
        "ordinance_number": "123/2026",
        "title": "LAUDO TÉCNICO DE EXPLICABILIDADE DE IA (XAI)",
        "mode": "XAI",
    }
    context = {
        "agent_id": "ALL",
        "scenario": "Operação em Tempo Real",
        "engine_version": "CARINA v1.0 (XAI Engine)",
        "image_path": "",
        "text_content": markdown,
    }

    success = docx_builder.generate_report(output_docx, context, config)
    assert success is True
    assert os.path.exists(output_docx)
    assert os.path.getsize(output_docx) > 0
