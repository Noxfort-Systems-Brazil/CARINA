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

# File: src/xai/report_metrics_transformer.py
# Author: Gabriel Moraes
# Date: August 14, 2026

from typing import Any, Dict, List


class ReportMetricsTransformer:
    """
    Transforms, normalizes, and ranks neural feature attributions and tensor metrics
    for consumption by report renderers.
    """

    @staticmethod
    def transform_agent_metrics(analyses: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        Calculates total feature importance sums, normalized percentages, and top contributors per agent.
        """
        transformed: Dict[str, Dict[str, Any]] = {}

        for aid, res in analyses.items():
            has_data = bool(res and res.get("has_tensor_data", True) and res.get("sorted_analysis"))
            if not has_data:
                transformed[aid] = {
                    "has_data": False,
                    "items": [],
                    "top_3": [],
                    "image_base64": res.get("image_base64") if res else None,
                }
                continue

            analysis = res["sorted_analysis"]
            total_imp = sum(abs(item.get("importance", 0.0)) for item in analysis) or 1.0

            items: List[Dict[str, Any]] = []
            for item in analysis:
                name = item.get("name", "Sensor")
                imp = abs(item.get("importance", 0.0))
                desc = item.get("description", "")
                pct = (imp / total_imp) * 100.0
                pct_str = f"{pct:.1f}%".replace(".", ",")

                items.append({"name": name, "importance": imp, "pct": pct, "pct_str": pct_str, "description": desc})

            # Top 3 most important features
            top_3 = sorted(items, key=lambda x: x["importance"], reverse=True)[:3]

            transformed[aid] = {
                "has_data": True,
                "items": items,
                "top_3": top_3,
                "image_base64": res.get("image_base64"),
            }

        return transformed
