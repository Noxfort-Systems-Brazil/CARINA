# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import Any, Dict, Optional


class EpisodeOverrideManager:
    """
    Manages operational state overrides, emergency manual commands,
    and hardware signal synchronization during simulation episodes.
    Follows Single Responsibility Principle (SRP).
    """

    @staticmethod
    def process_overrides(
        next_states_dict: Dict[str, Any],
        decision_coordinator: Any,
        action_supervisor: Optional[Any],
        current_operation_mode: str,
    ) -> str:
        """
        Parses operation_mode, override_commands, and active_overrides from state dict.
        Updates decision_coordinator and applies hardware overrides to action_supervisor.
        Returns the updated operation_mode.
        """
        if not next_states_dict:
            return current_operation_mode

        updated_mode = current_operation_mode
        if "operation_mode" in next_states_dict:
            updated_mode = next_states_dict["operation_mode"]

        if "override_commands" in next_states_dict:
            commands = next_states_dict.pop("override_commands")
            for command in commands:
                semaphore_id = command.get("semaphore_id")
                state = command.get("state")
                if semaphore_id and state:
                    decision_coordinator.override_states[semaphore_id] = state
                    if action_supervisor:
                        action_supervisor.apply_hardware_override(semaphore_id, state)

        if "active_overrides" in next_states_dict:
            decision_coordinator.override_states.clear()
            decision_coordinator.override_states.update(next_states_dict.get("active_overrides", {}))
            next_states_dict.pop("active_overrides", None)

        return updated_mode
