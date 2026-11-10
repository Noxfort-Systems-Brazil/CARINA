# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

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
