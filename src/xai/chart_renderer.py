# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Any, Dict, List

from rendering.mpl_utils import close_offscreen_figure, create_offscreen_figure, render_figure_to_png_bytes
from utils.locale_manager_backend import LocaleManagerBackend


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
        names = [x["name"] for x in sorted_analysis[:15]]
        values = [x["importance"] for x in sorted_analysis[:15]]

        fig, ax = create_offscreen_figure((10, 6), dpi=100)
        try:
            ax.barh(names, values, color="skyblue")

            xlabel_text = self.locale_manager.get_string("xai_report.chart_xlabel", default="Importance")
            if str(self.agent_id).upper() in ["ALL", "ALL_AGENTS", "TODOS", "REDE_GERAL"]:
                title_text = self.locale_manager.get_string(
                    "xai_report.chart_title_all",
                    default="Análise Geral de Importância — Rede Viária (Todos os Agentes)",
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

            fig.tight_layout()
            return render_figure_to_png_bytes(fig, close_fig=False, format="png")
        finally:
            close_offscreen_figure(fig)
