# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: ui/formatting/report_config_builder.py
# Author: Gabriel Moraes
# Date: September 2026

from typing import Any, Dict, List, Tuple

from ui.handlers.locale_manager import LocaleManager


class ReportConfigBuilder:
    """
    Constructs and resolves standardized configurations and legal/technical
    metadata directives for DOCX report exports (PLANNING, MFD, XAI).
    Follows Single Responsibility Principle (SRP).
    """

    @staticmethod
    def build_config(
        settings: Dict[str, Any], locale_manager: LocaleManager, mode: str
    ) -> Tuple[Dict[str, Any], List[str]]:
        """Builds configuration dictionary and block order list for the specified report mode."""

        def get_cfg(key: str, fallback_key: str, json_key: str, default_val: str) -> str:
            val = settings.get(key) or settings.get(fallback_key)
            if val is not None and str(val).strip() != "":
                return str(val)
            return locale_manager.get_string(f"xai_report.report_defaults.{json_key}", default=default_val)

        def clean_str(val: Any) -> str:
            return "" if val is None else str(val).replace("|", "").strip()

        if mode == "XAI":
            title = get_cfg("report_title", "xai_report_title", "title", "LAUDO TÉCNICO DE EXPLICABILIDADE DE IA (XAI)")
        elif mode == "MFD":
            title = get_cfg(
                "report_title_mfd", "xai_report_title_mfd", "title_mfd", "LAUDO TÉCNICO DE DESEMPENHO E OTIMIZAÇÃO MFD"
            )
        else:
            title = get_cfg(
                "report_title_planning",
                "planning_report_title",
                "title_planning",
                "LAUDO DESCRITIVO DE TRÁFEGO E INFRAESTRUTURA",
            )

        config = {
            "logo_path": settings.get("report_logo_path") or settings.get("xai_logo_path"),
            "secretary_name": clean_str(
                get_cfg("report_secretary_name", "xai_secretary_name", "secretary_name", "Dr. Gabriel Moraes")
            ),
            "secretary_title": clean_str(
                get_cfg(
                    "report_secretary_title",
                    "xai_secretary_title",
                    "secretary_title",
                    "Secretário de Mobilidade e Trânsito",
                )
            ),
            "agency_name": clean_str(
                get_cfg(
                    "report_agency_name",
                    "xai_agency_name",
                    "agency_name",
                    "Prefeitura Municipal / Secretaria de Trânsito",
                )
            ),
            "department_name": clean_str(
                get_cfg(
                    "report_department_name",
                    "xai_department_name",
                    "department_name",
                    "Departamento de Mobilidade Inteligente",
                )
            ),
            "ordinance_enabled": settings.get("report_ordinance_enabled"),
            "ordinance_number": settings.get("report_ordinance_number"),
            "city": settings.get("report_city"),
            "state_uf": settings.get("report_state_uf"),
            "title": title,
            "font_name": get_cfg("report_font_name", "xai_font_name", "font_name", "Arial"),
            "font_size": float(get_cfg("report_font_size", "xai_font_size", "font_size", "11")),
            "margin_top": float(get_cfg("report_margin_top", "xai_margin_top", "margin_top", "3.0")),
            "margin_bottom": float(get_cfg("report_margin_bottom", "xai_margin_bottom", "margin_bottom", "2.0")),
            "margin_left": float(get_cfg("report_margin_left", "xai_margin_left", "margin_left", "3.0")),
            "margin_right": float(get_cfg("report_margin_right", "xai_margin_right", "margin_right", "2.0")),
            "line_spacing": float(get_cfg("report_line_spacing", "xai_line_spacing", "line_spacing", "1.15")),
            "alignment": get_cfg("report_alignment", "xai_alignment", "alignment", "justify"),
            "locale_manager": locale_manager,
            "mode": mode,
        }

        if mode == "PLANNING":
            config["ementa_text"] = locale_manager.get_string(
                "structured_report.planning_ementa_text",
                default="Assunto: Análise da Capacidade Operacional, Avaliação de Warrants Técnicos (CONTRAN/MUTCD) e Recomendação Semafórica para a Malha Viária Urbana.",
            )
            config["metadata_title"] = locale_manager.get_string(
                "structured_report.planning_metadata_title", default="1. IDENTIFICAÇÃO E AMBIENTE OPERACIONAL"
            )
            config["chart_title"] = locale_manager.get_string(
                "structured_report.planning_chart_title", default="2. MAPA DE PLANEJAMENTO TÁTICO"
            )
            config["chart_caption"] = locale_manager.get_string(
                "structured_report.planning_chart_caption",
                default="Figura 1 – Mapa com Recomendações Espaciais da Malha Viária.",
            )
            config["content_fallback"] = locale_manager.get_string(
                "structured_report.planning_content_fallback",
                default="Nenhum laudo analítico de planejamento disponível.",
            )
            config["conformity_text"] = locale_manager.get_string(
                "structured_report.planning_conformity_text",
                default="Este documento foi consolidado pelo motor analítico CARINA SAS com base nos warrants técnicos (MUTCD / CONTRAN). Ele atesta as recomendações de engenharia de tráfego para a malha.",
            )
        elif mode == "MFD":
            config["ementa_text"] = locale_manager.get_string(
                "structured_report.mfd_ementa_text",
                default="Assunto: Análise da Capacidade Macroscópica da Rede, Diagrama Fundamental Macroscópico (MFD) e Avaliação de Nível de Serviço.",
            )
            config["metadata_title"] = locale_manager.get_string(
                "structured_report.mfd_metadata_title", default="1. IDENTIFICAÇÃO E AMBIENTE OPERACIONAL"
            )
            config["chart_title"] = locale_manager.get_string(
                "structured_report.mfd_chart_title",
                default="3. VISUALIZAÇÃO DO DIAGRAMA FUNDAMENTAL MACROSCÓPICO (MFD)",
            )
            config["chart_caption"] = locale_manager.get_string(
                "structured_report.mfd_chart_caption",
                default="Figura 1 – Curva de otimização MFD exibindo produção versus acumulação da malha viária.",
            )
            config["content_fallback"] = locale_manager.get_string(
                "structured_report.mfd_content_fallback", default="Nenhum laudo analítico MFD disponível."
            )
            config["conformity_text"] = locale_manager.get_string(
                "structured_report.mfd_conformity_text",
                default="Este laudo foi gerado de forma determinística pelo motor de otimização CARINA v1.0 (MFD Engine). Todos os cálculos foram executados por equações matemáticas auditáveis em Python e redigidos sob validação estrita de integridade técnico-gerencial.",
            )
        else:
            config["ementa_text"] = locale_manager.get_string(
                "structured_report.xai_ementa_text",
                default="Assunto: Auditoria de Inteligência Artificial, Explicabilidade Algorítmica (XAI) e Avaliação de Desempenho Operacional da Malha Semafórica Inteligente.",
            )

        block_order_str = get_cfg(
            "report_block_order", "xai_block_order", "block_order", "header,title,metadata,chart,content,signature"
        )
        block_order = [b.strip() for b in block_order_str.split(",") if b.strip()]

        return config, block_order
