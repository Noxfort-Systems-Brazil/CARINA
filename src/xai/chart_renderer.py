# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Any, Dict, List

import matplotlib.pyplot as plt

from utils.locale_manager_backend import LocaleManagerBackend

# Ensure matplotlib does not try to open windows (headless mode)
plt.switch_backend("Agg")


class ChartRenderer:
    """
    Responsibility: Render feature importance charts using matplotlib and save as PNG.
    """

    def __init__(self, agent_id: str, locale_manager: LocaleManagerBackend) -> None:
        self.agent_id = agent_id
        self.locale_manager = locale_manager

    def render(self, sorted_analysis: List[Dict[str, Any]], output_path: str) -> None:
        data = self.render_to_bytes(sorted_analysis)
        with open(output_path, "wb") as f:
            f.write(data)

    def render_to_bytes(self, sorted_analysis: List[Dict[str, Any]]) -> bytes:
        import io

        names = [x["name"] for x in sorted_analysis[:15]]
        values = [x["importance"] for x in sorted_analysis[:15]]

        plt.close("all")

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.barh(names, values, color="skyblue")

        xlabel_text = self.locale_manager.get_string("xai_report.chart_xlabel", default="Importance")
        if str(self.agent_id).upper() in ["ALL", "ALL_AGENTS", "TODOS", "REDE_GERAL"]:
            title_text = self.locale_manager.get_string(
                "xai_report.chart_title_all", default="Análise Geral de Importância — Rede Viária (Todos os Agentes)"
            )
        else:
            title_text = self.locale_manager.get_string(
                "xai_report.chart_title",
                default="Feature Importance Analysis - Agent {agent_id}",
                agent_id=self.agent_id,
            )

        ax.set_xlabel(xlabel_text)
        ax.set_title(title_text)
        ax.invert_yaxis()

        plt.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png")
        plt.close(fig)
        return buf.getvalue()
