# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import Any, Dict, List

from utils.locale_manager_backend import LocaleManagerBackend


class ReportWriter:
    """
    Responsibility: Format aggregated feature importance information
    and save as a structured text report.
    """

    def __init__(self, agent_id: str, locale_manager: LocaleManagerBackend) -> None:
        self.agent_id = agent_id
        self.locale_manager = locale_manager

    def write(self, sorted_analysis: List[Dict[str, Any]], output_path: str) -> None:
        data = self.write_to_string(sorted_analysis)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(data)

    def write_to_string(self, sorted_analysis: List[Dict[str, Any]]) -> str:
        lm = self.locale_manager
        lines = []
        lines.append("=" * 60)

        title = lm.get_string(
            "xai_report.title",
            default="Laudo Técnico de Explicabilidade Algorítmica XAI - Agente {agent_id}",
            agent_id=self.agent_id,
        )
        lines.append(title)

        subtitle = lm.get_string(
            "xai_report.subtitle",
            default="Data de Emissão: {timestamp}",
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        lines.append(subtitle)

        lines.append("=" * 60 + "\n")

        header_desc = lm.get_string(
            "xai_report.header_description",
            default="Este laudo apresenta o peso de importância matemática de cada sensor (variável) para o processo de tomada de decisão da Rede Neural Profunda, fundamentado no método de Gradientes Integrados (Captum).",
        )
        lines.append(header_desc + "\n")

        lbl_sensor = lm.get_string("xai_report.section_sensor", default="Sensor / Variável")
        lbl_importance = lm.get_string("xai_report.section_importance", default="Importância Relativa (Captum)")
        lbl_desc = lm.get_string("xai_report.section_description", default="Descrição Técnica")

        for item in sorted_analysis:
            bar_length = 20
            filled_length = int(item["normalized_importance"] * bar_length)
            bar = "█" * filled_length + "─" * (bar_length - filled_length)

            lines.append(f"● {lbl_sensor}: {item['name']}")
            lines.append(f"  {lbl_importance}: {bar} ({item['importance']:.4f})")
            lines.append(f"  {lbl_desc}: {item['description']}")
            lines.append("-" * 60)

        return "\n".join(lines)
