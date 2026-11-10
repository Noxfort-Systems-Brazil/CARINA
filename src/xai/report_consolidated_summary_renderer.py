# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Any, Dict, List

from xai.report_block_base import ReportBlockBase


class ReportConsolidatedSummaryRenderer(ReportBlockBase):
    """
    Renders network-wide consolidated neural attributions summary and global comparative chart.
    """

    def render(self, lines: List[str], block: Dict[str, Any], context: Dict[str, Any]) -> None:
        """Renders network-wide consolidated attributions and global chart."""
        agent_ids = context.get("agent_ids", [])
        metrics_by_agent = context.get("metrics_by_agent", {})
        global_image_base64 = context.get("global_image_base64")

        title_key = block.get("title_key", "")
        if title_key and self._t(title_key):
            lines.append(self._t(title_key))

        desc_key = block.get("desc_key", "")
        if desc_key and self._t(desc_key):
            lines.append(self._t(desc_key))
            lines.append("")

        if global_image_base64 and global_image_base64.strip():
            chart_cap = self._t(
                block.get("chart_caption", "global_chart_caption"),
                "Gráfico Geral de Atribuição Neural — Rede Viária (Todos os Agentes)",
            )
            lines.append(f"![{chart_cap}](data:image/png;base64,{global_image_base64})")
            lines.append("")

        item_tmpl = block.get("item_template", "consolidated_item")
        for aid in agent_ids:
            metric = metrics_by_agent.get(aid, {})
            if metric.get("has_data"):
                for item in metric.get("top_3", []):
                    name = item.get("name", "Sensor")
                    imp = item.get("importance", 0.0)
                    pct_str = item.get("pct_str", "0,0%")
                    item_str = self._t(
                        item_tmpl,
                        "- **{name} (Cruzamento ID {aid}):** Atribuição de **{pct_str}** ({imp:.4f}).",
                        name=name,
                        aid=aid,
                        pct_str=pct_str,
                        imp=imp,
                    )
                    lines.append(item_str)

        lines.append("")
