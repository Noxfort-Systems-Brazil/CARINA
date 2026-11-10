# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later
from typing import Any, Dict, List

from mfd.calculator import MFDCalculator


class MFDMetricsProcessor:
    """
    Computes per-step MFD metrics, intersection aggregations, and post-processes
    efficiency and congestion ratios relative to peak values.
    """

    @staticmethod
    def process_mfd_step_data(timestamp: str, edges_data: dict, edge_lengths: dict, edge_to_tl: dict) -> dict:
        """Calculates MFD metrics for a single simulation step."""
        lengths_dict = {
            edge_id: data.get("edge_length") or edge_lengths.get(edge_id, 100.0) for edge_id, data in edges_data.items()
        }

        production, accumulation, mean_speed, mean_density, mean_flow, active_edges = (
            MFDCalculator.compute_network_metrics(edges_data, lengths_dict, topology_loaded=True)
        )

        # Calculate intersection metrics
        tl_groups = {}
        for edge_id, data in edges_data.items():
            tl_id = edge_to_tl.get(edge_id)
            if tl_id:
                if tl_id not in tl_groups:
                    tl_groups[tl_id] = []
                tl_groups[tl_id].append((edge_id, data))

        intersections = {}
        for tl_id, edges_list in tl_groups.items():
            local_prod = 0.0
            local_accum = 0.0
            local_weighted_speed = 0.0
            local_total_len = 0.0
            local_queue = 0.0

            for edge_id, data in edges_list:
                length = lengths_dict.get(edge_id, 100.0)
                density = data.get("density", 0.0)
                speed = data.get("mean_speed", 0.0)
                occupancy = data.get("occupancy", 0.0)
                queue = data.get("queue_length", 0.0)

                if density <= 0 and occupancy > 0:
                    density = occupancy

                flow = density * speed
                local_prod += flow * length
                local_accum += density * length
                local_weighted_speed += speed * length
                local_total_len += length
                local_queue += queue

            avg_speed = (local_weighted_speed / local_total_len) if local_total_len > 0 else 0.0
            first_edge_data = edges_list[0][1] if edges_list else {}
            mat_stage = first_edge_data.get("maturity_stage", "CHILD")
            intersections[tl_id] = {
                "production": round(local_prod, 4),
                "accumulation": round(local_accum, 4),
                "mean_speed": round(avg_speed, 2),
                "queue_length": int(local_queue),
                "maturity_stage": mat_stage,
            }

        try:
            timestamp_val = float(timestamp)
        except ValueError:
            timestamp_val = timestamp

        return {
            "timestamp": timestamp_val,
            "accumulation": accumulation,
            "production": production,
            "mean_speed": mean_speed,
            "mean_density": mean_density,
            "mean_flow": mean_flow,
            "active_edges": active_edges,
            "intersections": intersections,
        }

    @staticmethod
    def post_process_history(history: List[Dict[str, Any]], peak_production: float, peak_accumulation: float):
        """Computes efficiency and congestion ratio for each step relative to peak values."""
        for snapshot in history:
            if peak_production > 0:
                snapshot["efficiency"] = min(snapshot["production"] / peak_production, 1.0)
            else:
                snapshot["efficiency"] = 1.0

            if peak_accumulation > 0:
                snapshot["congestion_ratio"] = snapshot["accumulation"] / peak_accumulation
            else:
                snapshot["congestion_ratio"] = 0.0
