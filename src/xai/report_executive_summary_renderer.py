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

# File: src/xai/report_executive_summary_renderer.py
# Author: Gabriel Moraes
# Date: August 14, 2026

from typing import Any, Dict, List

from xai.report_block_base import ReportBlockBase


class ReportExecutiveSummaryRenderer(ReportBlockBase):
    """
    Renders Part I — Executive Summary for public administration and decision makers,
    including strategic urban highlights and synthetic management table per intersection.
    """

    def render(self, lines: List[str], block: Dict[str, Any], context: Dict[str, Any]) -> None:
        agent_ids = context.get("agent_ids", [])
        guardian_stats = context.get("guardian_stats", {})
        metrics_by_agent = context.get("metrics_by_agent", {})
        total_agents = len(agent_ids)

        # 1. Main Part I Title
        title_key = block.get("title_key", "exec_part_title")
        if title_key and self._t(title_key):
            lines.append(self._t(title_key))

        # 2. Objective Subsections
        obj_title_key = block.get("obj_title_key", "exec_obj_title")
        if obj_title_key and self._t(obj_title_key):
            lines.append(self._t(obj_title_key))

        obj_desc_key = block.get("obj_desc_key", "exec_obj_desc")
        if obj_desc_key and self._t(obj_desc_key):
            lines.append(self._t(obj_desc_key, total_agents=total_agents))
            lines.append("")

        # 3. Highlights Subsections
        highlights_title_key = block.get("highlights_title_key", "exec_highlights_title")
        if highlights_title_key and self._t(highlights_title_key):
            lines.append(self._t(highlights_title_key))

        # Calculate network aggregate stats
        total_eval = sum(stats.get("eval_count", 0) for stats in guardian_stats.values())
        total_critical = sum(stats.get("critical_count", 0) for stats in guardian_stats.values())

        highlights_desc_key = block.get("highlights_desc_key", "exec_highlights_desc")
        if highlights_desc_key and self._t(highlights_desc_key):
            lines.append(
                self._t(
                    highlights_desc_key,
                    total_agents=total_agents,
                    total_eval=f"{total_eval:,}".replace(",", ".") if total_eval else "0",
                    total_critical=total_critical,
                )
            )
            lines.append("")

        # 4. Synthetic Table
        table_title_key = block.get("table_title_key", "exec_table_title")
        if table_title_key and self._t(table_title_key):
            lines.append(self._t(table_title_key))

        table_hdr = self._t(
            block.get("header_template", "executive_table_header"),
            "| {col_exec_intersection} | {col_exec_agent} | {col_exec_focus} | {col_exec_compliance} | {col_exec_opinion} |\n| :--- | :---: | :--- | :---: | :--- |",
            col_exec_intersection=self._t("col_exec_intersection", "Cruzamento / Interseção"),
            col_exec_agent=self._t("col_exec_agent", "Agente ID"),
            col_exec_focus=self._t("col_exec_focus", "Foco Principal da Decisão"),
            col_exec_compliance=self._t("col_exec_compliance", "Índice de Conformidade de Segurança"),
            col_exec_opinion=self._t("col_exec_opinion", "Parecer Executivo"),
        )
        lines.append(table_hdr)

        row_template = block.get("row_template", "executive_table_row")
        for idx, aid in enumerate(agent_ids, 1):
            stats = guardian_stats.get(
                aid,
                {
                    "eval_count": 0,
                    "approved_count": 0,
                    "temporal_count": 0,
                    "critical_count": 0,
                    "rate_str": "100,0%",
                    "approved_pct": "100,0",
                },
            )
            metric = metrics_by_agent.get(aid, {})

            # Resolve decision focus string from top 2 features
            focus_parts = []
            if metric.get("has_data") and metric.get("top_3"):
                for it in metric["top_3"][:2]:
                    fname = it.get("name", "").split("(")[0].strip()
                    fpct = it.get("pct_str", "0,0%")
                    focus_parts.append(f"{fname} ({fpct})")
            focus_str = (
                " + ".join(focus_parts)
                if focus_parts
                else self._t("table_missing_data_factor", "Aguardando Amostragem")
            )

            # Compliance string
            crit = stats.get("critical_count", 0)
            rate_str = stats.get("rate_str", "100,0%")
            if crit == 0:
                compliance_str = self._t("exec_compliance_safe", "100% Seguro ({rate_str} Direto)", rate_str=rate_str)
            else:
                compliance_str = self._t(
                    "exec_compliance_warning", "{rate_str} ({crit} Vetos Críticos)", rate_str=rate_str, crit=crit
                )

            opinion_str = (
                self._t("exec_opinion_approved", "**Homologado com Excelência**")
                if crit == 0
                else self._t("exec_opinion_warning", "**Aprovado com Ressalvas**")
            )

            c_label = self._t("agent_short_label", f"Cruzamento {idx:02d}", idx=idx, aid=aid)

            row_str = self._t(
                row_template,
                "| {c_label} | `{aid}` | {focus_str} | {compliance_str} | {opinion_str} |",
                c_label=c_label,
                aid=aid,
                focus_str=focus_str,
                compliance_str=compliance_str,
                opinion_str=opinion_str,
            )
            lines.append(row_str)

        lines.append("")
