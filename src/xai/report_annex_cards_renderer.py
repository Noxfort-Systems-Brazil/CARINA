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

# File: src/xai/report_annex_cards_renderer.py
# Author: Gabriel Moraes
# Date: August 14, 2026

from typing import Any, Dict, List

from xai.report_block_base import ReportBlockBase


class ReportAnnexCardsRenderer(ReportBlockBase):
    """
    Renders Annex I per-intersection individual explainability sheets, sensor rankings,
    safety audits, and expert technical opinions.
    """

    def render(self, lines: List[str], block: Dict[str, Any], context: Dict[str, Any]) -> None:
        """Renders Annex I individual intersection explainability sheets."""
        agent_ids = context.get("agent_ids", [])
        guardian_stats = context.get("guardian_stats", {})
        metrics_by_agent = context.get("metrics_by_agent", {})

        title_key = block.get("title_key", "")
        if title_key and self._t(title_key):
            lines.append(self._t(title_key))

        desc_key = block.get("desc_key", "")
        if desc_key and self._t(desc_key):
            lines.append(self._t(desc_key))
            lines.append("")

        for idx, aid in enumerate(agent_ids, 1):
            metric = metrics_by_agent.get(aid, {})
            has_data = metric.get("has_data", False)

            lines.append(
                self._t(
                    block.get("card_header", "agent_card_header"),
                    f"#### Cruzamento {idx:02d} — Agente ID {aid}",
                    idx=idx,
                    aid=aid,
                )
            )

            if has_data:
                lines.append(self._t(block.get("card_intro", "agent_card_intro"), "A análise pericial...", aid=aid))
                lines.append("")
                for item in metric.get("items", []):
                    lines.append(
                        self._t(
                            block.get("card_item", "agent_card_item"),
                            "- **{name}:** {pct_str}",
                            name=item.get("name", "Sensor"),
                            pct_str=item.get("pct_str", "0,0%"),
                            imp=item.get("importance", 0.0),
                            desc=item.get("description", ""),
                        )
                    )
            else:
                lines.append(
                    self._t(
                        block.get("card_missing_data", "agent_card_missing_data"),
                        "Atenção: Ausência de dados de amostragem no Cruzamento ID {aid}.",
                        aid=aid,
                    )
                )

            lines.append("")

            stats = guardian_stats.get(
                aid,
                {
                    "eval_count": 0,
                    "approved_count": 0,
                    "temporal_count": 0,
                    "critical_count": 0,
                    "approved_pct": "100,0",
                    "reason": self._t("table_missing_data_action", "Aguardando Amostragem"),
                },
            )

            lines.append(
                self._t(
                    block.get("guardian_card_audit", "guardian_card_audit"),
                    "- **Auditoria do Agente Guardião (D3QN):**...",
                    eval_count=stats.get("eval_count", 0),
                    approved_count=stats.get("approved_count", 0),
                    approved_pct=stats.get("approved_pct", "100,0"),
                    temporal_count=stats.get("temporal_count", 0),
                    critical_count=stats.get("critical_count", 0),
                    veto_reason=stats.get("reason", self._t("table_missing_data_action", "Aguardando Amostragem")),
                )
            )

            lines.append(
                self._t(
                    block.get("pae_card_audit", "pae_card_audit"),
                    "- **Auditoria do Agente Consultor (PAE 128 canais):**...",
                )
            )
            lines.append("")
            lines.append(
                self._t(block.get("agent_card_opinion", "agent_card_opinion"), "**Parecer Pericial...**", aid=aid)
            )

            # Only render individual chart in Annex I if multiple agents exist in network
            # For single-agent reports, the chart is already presented in the consolidated summary
            if has_data and len(agent_ids) > 1:
                img_b64 = metric.get("image_base64")
                if img_b64 and img_b64.strip():
                    lines.append("")
                    card_img_cap = self._t(
                        block.get("agent_card_chart_caption", "agent_card_chart_caption"),
                        "Gráfico Pericial de Atribuição Neural — Cruzamento ID {aid}",
                        aid=aid,
                    )
                    lines.append(f"![{card_img_cap}](data:image/png;base64,{img_b64})")
                    lines.append("")

            lines.append("")
