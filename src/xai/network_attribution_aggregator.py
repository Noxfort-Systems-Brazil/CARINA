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

# File: src/xai/network_attribution_aggregator.py
# Author: Gabriel Moraes
# Date: August 14, 2026

import base64
import logging
import os
from typing import Any, Dict, List, Optional

from utils.locale_manager_backend import LocaleManagerBackend
from xai.chart_renderer import ChartRenderer


class NetworkAttributionAggregator:
    """
    Mathematical aggregation engine for Explainable AI (XAI).
    Computes network-wide weighted mean attributions across all intersection controllers
    and renders consolidated multi-agent feature importance charts.
    """

    def __init__(self, scenario_results_dir: str, locale_manager: Optional[LocaleManagerBackend] = None) -> None:
        self.scenario_results_dir = scenario_results_dir
        self.locale_manager = locale_manager if locale_manager is not None else LocaleManagerBackend()

    def aggregate_network_analysis(self, analyses_by_agent: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aggregates individual agent attribution dictionaries into a single network-wide analysis.
        Renders and returns the consolidated base64 chart image.
        """
        if not analyses_by_agent:
            return {"global_image_base64": "", "aggregated_analysis": []}

        category_totals: Dict[str, float] = {}
        category_descriptions: Dict[str, str] = {}
        valid_agent_count = 0

        for res in analyses_by_agent.values():
            analysis = res.get("sorted_analysis", [])
            if analysis:
                valid_agent_count += 1
                for item in analysis:
                    name = item.get("name", "Auxiliary Control")
                    imp = float(item.get("importance", 0.0))
                    desc = item.get("description", "")
                    category_totals[name] = category_totals.get(name, 0.0) + imp
                    if desc and name not in category_descriptions:
                        category_descriptions[name] = desc

        if valid_agent_count == 0 or not category_totals:
            return {"global_image_base64": "", "aggregated_analysis": []}

        aggregated_analysis: List[Dict[str, Any]] = [
            {
                "name": name,
                "importance": total_imp / valid_agent_count,
                "description": category_descriptions.get(name, ""),
            }
            for name, total_imp in category_totals.items()
        ]
        aggregated_analysis = sorted(aggregated_analysis, key=lambda x: x["importance"], reverse=True)

        # Render network-wide consolidated chart
        chart_renderer = ChartRenderer("ALL", self.locale_manager)
        img_bytes = chart_renderer.render_to_bytes(aggregated_analysis)
        global_image_base64 = base64.b64encode(img_bytes).decode("utf-8")

        # Persist aggregated chart to disk as fallbacks for legacy/UI export compatibility
        try:
            p1 = os.path.join(self.scenario_results_dir, "xai_importance.png")
            p2 = os.path.join(self.scenario_results_dir, "plots", "xai_importance.png")
            os.makedirs(os.path.dirname(p2), exist_ok=True)
            with open(p1, "wb") as f1:
                f1.write(img_bytes)
            with open(p2, "wb") as f2:
                f2.write(img_bytes)
        except Exception as ex_file:
            logging.warning(f"[NetworkAttributionAggregator] Non-fatal: Could not write xai_importance.png: {ex_file}")

        return {"global_image_base64": global_image_base64, "aggregated_analysis": aggregated_analysis}
