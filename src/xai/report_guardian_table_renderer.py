# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Any, Dict, List

from xai.report_block_base import ReportBlockBase


class ReportGuardianTableRenderer(ReportBlockBase):
    """
    Renders Guardian D3QN safety compliance tables and veto statistics in Markdown.
    """

    def render(self, lines: List[str], block: Dict[str, Any], context: Dict[str, Any]) -> None:
        """Renders Guardian D3QN safety compliance table."""
        agent_ids = context.get("agent_ids", [])
        guardian_stats = context.get("guardian_stats", {})

        title_key = block.get("title_key", "")
        if title_key and self._t(title_key):
            lines.append(self._t(title_key))

        desc_key = block.get("desc_key", "")
        if desc_key and self._t(desc_key):
            lines.append(self._t(desc_key))
            lines.append("")

        table_hdr = self._t(
            block.get("header_template", "guardian_table_header"),
            "| {col_guardian_id} | {col_guardian_eval} | {col_guardian_approved} | {col_guardian_temporal} | {col_guardian_critical} | {col_guardian_rate} | {col_guardian_reason} |\n| :--- | :---: | :---: | :---: | :---: | :---: | :--- |",
            col_guardian_id=self._t("col_guardian_id", "Cruzamento / Agente"),
            col_guardian_eval=self._t("col_guardian_eval", "Avaliações"),
            col_guardian_approved=self._t("col_guardian_approved", "Aprovados"),
            col_guardian_temporal=self._t("col_guardian_temporal", "Intervenções Temporais"),
            col_guardian_critical=self._t("col_guardian_critical", "Vetos Críticos"),
            col_guardian_rate=self._t("col_guardian_rate", "Taxa Conformidade"),
            col_guardian_reason=self._t("col_guardian_reason", "Motivo Predominante"),
        )
        lines.append(table_hdr)

        row_template = block.get("row_template", "guardian_table_row")
        for aid in agent_ids:
            stats = guardian_stats.get(
                aid,
                {
                    "eval_count": 0,
                    "approved_count": 0,
                    "temporal_count": 0,
                    "critical_count": 0,
                    "rate_str": "100,0%",
                    "reason": self._t("table_missing_data_factor", "Aguardando Amostragem"),
                },
            )

            c_label = self._t("agent_label", f"Cruzamento ID {aid}", aid=aid)
            row_str = self._t(
                row_template,
                "| {c_label} | {eval_count} | {approved_count} | {temporal_count} | {critical_count} | {rate_str} | {reason} |",
                c_label=c_label,
                eval_count=stats.get("eval_count", 0),
                approved_count=stats.get("approved_count", 0),
                temporal_count=stats.get("temporal_count", 0),
                critical_count=stats.get("critical_count", 0),
                rate_str=stats.get("rate_str", "100,0%"),
                reason=stats.get("reason", self._t("table_missing_data_factor", "Aguardando Amostragem")),
            )
            lines.append(row_str)

        lines.append("")
