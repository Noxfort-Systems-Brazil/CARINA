# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import queue
from typing import Dict, Tuple


class OverrideStateManager:
    """
    Responsible for managing manual command queues and tracking the override
    state for map elements (streets and traffic lights).
    """

    def __init__(self):
        self.command_queue = queue.Queue()
        self.semaphore_overrides: Dict[str, str] = {}
        self.street_overrides: Dict[str, str] = {}

    def enqueue_command(self, command: dict):
        self.command_queue.put(command)

    def process_queue(self):
        """Empties the queue and updates the override dictionaries."""
        while not self.command_queue.empty():
            try:
                cmd = self.command_queue.get_nowait()
                cmd_type = cmd.get("type", "semaphore")
                cmd_id = cmd.get("id")
                cmd_state = cmd.get("state")

                if cmd_type == "street":
                    if cmd_state == "NORMAL":
                        self.street_overrides.pop(cmd_id, None)
                    else:
                        self.street_overrides[cmd_id] = cmd_state
                else:
                    if cmd_state == "NORMAL":
                        self.semaphore_overrides.pop(cmd_id, None)
                    else:
                        self.semaphore_overrides[cmd_id] = cmd_state
            except queue.Empty:
                break

    def get_semaphore_overrides(self) -> Dict[str, str]:
        return self.semaphore_overrides

    def get_street_overrides(self) -> Dict[str, str]:
        return self.street_overrides
