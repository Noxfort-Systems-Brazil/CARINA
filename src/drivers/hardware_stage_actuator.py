# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Any, Dict, List, Optional


class HardwareStageActuator:
    """
    Coordinates hardware driver actuation and color logging for traffic lights.
    Respects manual overrides, state reconciliation, and sends hold commands on valid green stage shifts
    while leaving intergreen (yellow/all-red) clearances unheld for hardware safety timing.
    """

    def __init__(self):
        self.last_commanded_stages: Dict[str, int] = {}

    def reset(self):
        """Clears the history of commanded stages."""
        self.last_commanded_stages.clear()

    @staticmethod
    def _lookup_tl_entry(mapping: Any, tl_id: str) -> Any:
        if not isinstance(mapping, dict):
            return None
        s_id = str(tl_id)
        alt_id = s_id[3:] if s_id.startswith("tl_") else f"tl_{s_id}"
        for key in (s_id, alt_id):
            if key in mapping:
                return mapping[key]
        return None

    @staticmethod
    def _is_intergreen_stage(stage_idx: int, stage_codes: Any, green_stages: Any) -> bool:
        """Returns True when stage_idx represents a yellow or all-red intergreen stage."""
        if isinstance(green_stages, (list, tuple)) and len(green_stages) > 0:
            if stage_idx not in green_stages:
                return True
        if isinstance(stage_codes, dict) and stage_idx in stage_codes:
            state_str = str(stage_codes[stage_idx]).lower()
            if state_str and "g" not in state_str:
                return True
        return False

    def sync_hardware_stages(
        self,
        action_supervisor: Any,
        current_stages: Dict[str, Any],
        state_extractor: Any,
        state_reconciler: Optional[Any] = None,
    ) -> None:
        """
        Synchronizes stage holds on green stages and logs carina colors to active hardware drivers
        only when an intersection transitions to a different stage.
        """
        if not hasattr(action_supervisor, "connection_manager"):
            return

        active_connections = action_supervisor.connection_manager.active_connections
        if not isinstance(active_connections, dict):
            return
        active_ids = set(active_connections.keys())

        # Purge stale IDs no longer active
        for old_id in list(self.last_commanded_stages.keys()):
            if old_id not in active_ids:
                self.last_commanded_stages.pop(old_id, None)

        for tl_id, driver in active_connections.items():
            current_stage_idx = self._lookup_tl_entry(current_stages, tl_id)
            if current_stage_idx is None:
                current_stage_idx = 0

            # Safety Check: Is inference/actuation allowed for this intersection?
            if state_reconciler and not state_reconciler.is_inference_allowed(tl_id):
                state_reconciler.on_stage_transition_detected(tl_id, current_stage_idx)
                if not state_reconciler.is_inference_allowed(tl_id):
                    continue

            # If the traffic light has an active manual override, skip automatic commands
            override_state = self._lookup_tl_entry(getattr(action_supervisor, "override_states", {}), tl_id)
            if override_state in ("ALERT", "OFF"):
                self.last_commanded_stages.pop(tl_id, None)
                continue

            stage_codes = self._lookup_tl_entry(getattr(state_extractor, "tl_stage_codes", {}), tl_id) or {}
            green_stages = self._lookup_tl_entry(getattr(state_extractor, "tl_green_stages", {}), tl_id) or []

            # Send command and log only when the stage changes
            if tl_id not in self.last_commanded_stages or self.last_commanded_stages[tl_id] != current_stage_idx:
                self.last_commanded_stages[tl_id] = current_stage_idx
                if not self._is_intergreen_stage(current_stage_idx, stage_codes, green_stages):
                    action_supervisor.send_stage_hold(tl_id, current_stage_idx)

                if hasattr(driver, "log_carina_colors"):
                    driver.log_carina_colors(current_stage_idx, stage_codes)
