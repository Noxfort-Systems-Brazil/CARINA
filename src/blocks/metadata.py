# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Any, Dict

from .base import ReportBlock, get_translated

try:
    from docx.shared import Pt, RGBColor
except ImportError:
    pass


class MetadataBlock(ReportBlock):
    """Creates a structured metadata table with information regarding the agent or run under analysis."""

    def build(self, doc: Any, context: Dict[str, Any], config: Dict[str, Any]) -> None:
        agent_id = context.get("agent_id", "UNKNOWN")
        scenario = context.get("scenario", "Live Session")
        engine_ver = context.get("engine_version", "CARINA v1.0.0")

        mode = config.get("mode", "XAI")

        metadata_title = config.get("metadata_title")
        metadata_rows = context.get("metadata_rows") or config.get("metadata_rows")

        font_size = float(config.get("font_size", 11.0))

        clean_agent_id = str(agent_id).replace("|", "").strip()
        if clean_agent_id.upper() in ["ALL", "ALL_AGENTS", "TODOS", "UNKNOWN", ""]:
            display_agent = get_translated(
                config, "structured_report.xai_all_agents_label", "Todos os Agentes (Rede Completa)"
            )
        else:
            display_agent = clean_agent_id

        if metadata_title is not None and metadata_rows is not None:
            heading = metadata_title
            headers = metadata_rows
        elif mode == "MFD":
            heading = get_translated(
                config, "structured_report.mfd_metadata_title", "1. AMBIENTE OPERACIONAL E IDENTIFICAÇÃO"
            )
            headers = [
                (get_translated(config, "structured_report.mfd_label_scenario", "Cenário de Simulação:"), scenario),
                (get_translated(config, "structured_report.mfd_label_engine", "Motor Analítico MFD:"), engine_ver),
                (get_translated(config, "structured_report.mfd_label_control", "Sistema de Controle:"), display_agent),
            ]
        else:
            heading = get_translated(
                config, "structured_report.xai_metadata_title", "1. AMBIENTE OPERACIONAL E IDENTIFICAÇÃO"
            )
            headers = [
                (
                    get_translated(config, "structured_report.xai_label_agent", "Identificador do Agente:"),
                    display_agent,
                ),
                (get_translated(config, "structured_report.xai_label_scenario", "Cenário de Operação:"), scenario),
                (get_translated(config, "structured_report.xai_label_engine", "Motor Analítico:"), engine_ver),
            ]
        clean_heading = str(heading).replace("|", "").strip()
        if not clean_heading.startswith("1."):
            clean_heading = f"1. {clean_heading}"

        h = doc.add_paragraph()
        h.paragraph_format.space_before = Pt(12)
        h.paragraph_format.space_after = Pt(6)
        run_h = h.add_run(clean_heading)
        run_h.bold = True
        run_h.font.size = Pt(font_size)
        run_h.font.color.rgb = RGBColor(0, 0, 0)

        table = doc.add_table(rows=len(headers), cols=2)
        table.style = "Table Grid"

        for idx, (label, val) in enumerate(headers):
            clean_lbl = str(label).replace("|", "").strip()
            clean_val = str(val).replace("|", "").strip()

            cell_label = table.cell(idx, 0)
            run_lbl = cell_label.paragraphs[0].add_run(clean_lbl)
            run_lbl.bold = True
            run_lbl.font.size = Pt(10)
            run_lbl.font.color.rgb = RGBColor(0, 0, 0)

            cell_val = table.cell(idx, 1)
            run_val = cell_val.paragraphs[0].add_run(clean_val)
            run_val.font.size = Pt(10)
            run_val.font.color.rgb = RGBColor(0, 0, 0)

        doc.add_paragraph().paragraph_format.space_after = Pt(6)
