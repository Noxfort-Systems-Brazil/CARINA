# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2025 Gabriel Moraes - Noxfort Systems
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

# File: src/sds/telemetry_aggregator.py
# Author: Gabriel Moraes - Noxfort Systems
# Date: 12/24/2025

import logging
import time
from typing import Dict, Any, Optional

class TelemetryAggregator:
    """
    Responsible for aggregating high-frequency traffic data into periodic
    updates for the Smart Dashboard Service (SDS).
    
    This class isolates the visualization logic (heatmap weights, normalization)
    from the core control logic.
    """

    def __init__(self, update_interval: float = 2.0):
        """
        Args:
            update_interval (float): Minimum seconds between visual updates.
        """
        self.update_interval = update_interval
        self.last_update_time = 0.0
        
        # Buffer structure: {edge_id: {'occ': float, 'spd': float, 'q': float, 'count': int}}
        self.heatmap_buffer: Dict[str, Dict[str, float]] = {}
        
        # Visualization settings
        # These weights determine how 'red' an edge looks on the dashboard
        self.heatmap_weights = {
            'occupancy': 1.0, 
            'queue': 0.8, 
            'speed': -0.5
        }

    def process_frame(self, frame) -> None:
        """
        Accumulates data from a single traffic frame into the aggregation buffer.
        """
        # If this is the first frame, initialize the timer
        if self.last_update_time == 0.0:
            self.last_update_time = frame.timestamp

        for edge_id, state in frame.edges.items():
            if edge_id not in self.heatmap_buffer:
                self.heatmap_buffer[edge_id] = {'occ': 0.0, 'spd': 0.0, 'q': 0.0, 'count': 0}
            
            buf = self.heatmap_buffer[edge_id]
            buf['occ'] += state.occupancy
            buf['spd'] += state.mean_speed
            buf['q'] += state.queue_length
            buf['count'] += 1

    def should_update(self, current_time: float) -> bool:
        """
        Checks if enough time has passed to trigger a dashboard update.
        """
        return (current_time - self.last_update_time) >= self.update_interval

    def compute_rich_payload(self, current_time: float, maturity_cache: Dict[str, str]) -> Dict[str, Any]:
        """
        Generates the 'rich' payload containing averaged metrics and maturity states
        for the UI. Resets the buffer after computation.

        Args:
            current_time (float): The current simulation/system time.
            maturity_cache (Dict): Current maturity state of agents (e.g. {'tls_1': 'ADULT'}).

        Returns:
            Dict: The payload ready to be sent to the SDS queue.
        """
        rich_payload = {
            'timestamp': current_time,
            'edges': {},
            'maturity': maturity_cache
        }
        
        for edge_id, buf in self.heatmap_buffer.items():
            count = buf['count']
            if count > 0:
                # Average calculations
                avg_occ = buf['occ'] / count
                avg_spd = buf['spd'] / count
                avg_q = buf['q'] / count
                
                # Normalization logic for visualization
                # Queue: Normalized against 20 vehicles (arbitrary visual cap)
                norm_q = min(avg_q / 20.0, 1.0)
                # Speed: Normalized against ~50km/h (13.89 m/s)
                norm_spd = min(avg_spd / 13.89, 1.0)
                
                # Weighted Heat Score
                heat_val = (avg_occ * self.heatmap_weights['occupancy']) + \
                           (norm_q * self.heatmap_weights['queue']) + \
                           (norm_spd * self.heatmap_weights['speed'])
                
                rich_payload['edges'][edge_id] = {
                    'congestion': max(0.0, heat_val),
                    'speed': avg_spd * 3.6, # Convert m/s to km/h for display
                    'vehicles': int(avg_q),
                    'flow': 0 # Flow is calculated differently, usually kept 0 here for HFT
                }
        
        # Reset state for next cycle
        self.heatmap_buffer.clear()
        self.last_update_time = current_time
        
        return rich_payload
    
    def reset(self):
        """Manually clears the buffer."""
        self.heatmap_buffer.clear()
        self.last_update_time = 0.0