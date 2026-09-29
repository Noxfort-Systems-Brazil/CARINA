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

# File: src/engine/hardware_stage_actuator.py
# Author: Gabriel Moraes
# Date: September 2026

from typing import Any, Dict, Optional


class HardwareStageActuator:
    """
    Coordinates hardware driver actuation and color logging for traffic lights.
    Respects manual overrides, state reconciliation, and sends hold commands on phase shifts.
    """

    def __init__(self):
        self.last_commanded_stages: Dict[str, int] = {}

    def reset(self):
        """Clears the history of commanded stages."""
        self.last_commanded_stages.clear()

    def sync_hardware_stages(
        self,
        action_supervisor: Any,
        current_stages: Dict[str, Any],
        state_extractor: Any,
        state_reconciler: Optional[Any] = None,
    ) -> None:
        """
        Synchronizes stage holds and logs carina colors to active hardware drivers
        only when an intersection transitions to a different stage.
        """
        if not hasattr(action_supervisor, "connection_manager"):
            return

        active_connections = action_supervisor.connection_manager.active_connections
        active_ids = set(active_connections.keys())

        # Purge stale IDs no longer active
        for old_id in list(self.last_commanded_stages.keys()):
            if old_id not in active_ids:
                self.last_commanded_stages.pop(old_id, None)

        for tl_id, driver in active_connections.items():
            current_stage_idx = current_stages.get(tl_id, 0)

            # Safety Check: Is inference/actuation allowed for this intersection?
            if state_reconciler and not state_reconciler.is_inference_allowed(tl_id):
                continue

            # If the traffic light has an active manual override, skip automatic commands
            override_state = getattr(action_supervisor, "override_states", {}).get(tl_id)
            if override_state in ("ALERT", "OFF"):
                self.last_commanded_stages.pop(tl_id, None)
                continue

            # Send command and log only when the stage changes
            if tl_id not in self.last_commanded_stages or self.last_commanded_stages[tl_id] != current_stage_idx:
                self.last_commanded_stages[tl_id] = current_stage_idx
                action_supervisor.send_stage_hold(tl_id, current_stage_idx)

                stage_codes = getattr(state_extractor, "tl_stage_codes", {}).get(tl_id, {})
                if hasattr(driver, "log_carina_colors"):
                    driver.log_carina_colors(current_stage_idx, stage_codes)
