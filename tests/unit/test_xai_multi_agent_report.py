# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: tests/unit/test_xai_multi_agent_report.py
# Author: Gabriel Moraes
# Date: September 2026

import os

from blocks.structured_report_builder import StructuredReportBuilder
from utils.locale_manager_backend import LocaleManagerBackend
from xai.multi_agent_report_builder import MultiAgentReportBuilder
from xai.report_executive_summary_renderer import ReportExecutiveSummaryRenderer
from xai.xai_template_repository import XaiTemplateRepository


def test_xai_executive_summary_renderer_rendering():
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
