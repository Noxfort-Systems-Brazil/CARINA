# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
MFD Processor & Step Orchestrator.

Handles runtime macroscopic fundamental diagram (MFD) calculations, step processing,
and delegates database reconstruction to MFDHistoryReconstructor.
"""

import logging
from typing import Any, Dict, Optional

from mfd.mfd_db_fetcher import MFDDataFetcher
from mfd.mfd_history_reconstructor import MFDHistoryReconstructor
from mfd.mfd_metrics_processor import MFDMetricsProcessor
from mfd.mfd_network_parser import MFDNetworkParser


class MFDProcessor:
    """Handles macroscopic fundamental diagram (MFD) calculations, step processing, and persistence."""

    def __init__(self, mfd: Any, state_extractor: Any) -> None:
        self.mfd = mfd
        self.state_extractor = state_extractor

    def reset(self) -> None:
        """Resets the MFD history and resets internal MFD state."""
        if self.mfd and hasattr(self.mfd, "reset"):
            self.mfd.reset()

    def get_latest_efficiency(self) -> float:
        """Returns the efficiency score from the latest MFD calculation."""
        if self.mfd and hasattr(self.mfd, "get_latest"):
            latest = self.mfd.get_latest()
            if latest and hasattr(latest, "efficiency"):
                return latest.efficiency
        return 0.0

    def process_step(
        self, edges_data: Dict[str, Any], sim_time: float, agents_keys: list, step_counter: int, episode_steps: int
    ) -> Optional[Dict[str, Any]]:
        """Computes MFD metrics for the network and individual intersections, and persists history at episode boundaries."""
        if not self.mfd or not edges_data:
            return None

        intersection_metrics = {}
        if hasattr(self.state_extractor, "tl_incoming_edges"):
            for tl_id in agents_keys:
                incoming = self.state_extractor.tl_incoming_edges.get(tl_id, [])
                local_prod = 0.0
                local_accum = 0.0
                local_weighted_speed = 0.0
                local_total_len = 0.0
                local_queue = 0.0

                for edge_id in incoming:
                    if edge_id in edges_data:
                        edge_info = edges_data[edge_id]
                        length = self.mfd._edge_lengths.get(edge_id, 100.0)

                        density = edge_info.get("density", 0.0)
                        speed = edge_info.get("mean_speed", 0.0)
                        occupancy = edge_info.get("occupancy", 0.0)
                        queue = edge_info.get("queue_length", 0.0)

                        if density <= 0 and occupancy > 0:
                            density = occupancy

                        flow = density * speed
                        local_prod += flow * length
                        local_accum += density * length
                        local_weighted_speed += speed * length
                        local_total_len += length
                        local_queue += queue

                avg_speed = (local_weighted_speed / local_total_len) if local_total_len > 0 else 0.0
                intersection_metrics[tl_id] = {
                    "production": round(local_prod, 4),
                    "accumulation": round(local_accum, 4),
                    "mean_speed": round(avg_speed, 2),
                    "queue_length": int(local_queue),
                }

        mfd_snapshot = self.mfd.compute_step(edges_data, sim_time, intersections=intersection_metrics)
        mfd_data = mfd_snapshot.to_dict()

        # Log network state at episode boundaries
        if step_counter % episode_steps == 0:
            report = self.mfd.get_network_report()
            if report.get("status") == "OK":
                state = report["network_state"]
                eff = report["current"].get("efficiency", 0)
                logging.info(
                    f"[MFD] Network State: {state} | "
                    f"Efficiency: {eff:.1%} | "
                    f"Production: {mfd_snapshot.production:.2f} veh·m/s | "
                    f"Accumulation: {mfd_snapshot.accumulation:.2f} veh"
                )

        return mfd_data


__all__ = [
    "MFDProcessor",
    "MFDNetworkParser",
    "MFDDataFetcher",
    "MFDMetricsProcessor",
    "MFDHistoryReconstructor",
]
