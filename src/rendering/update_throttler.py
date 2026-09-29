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

# File: src/rendering/update_throttler.py
# Author: Gabriel Moraes
# Date: September 2026

import threading
import time
from typing import Any, Callable, Optional, Tuple


class UpdateThrottler:
    """Controls the update rate to avoid interface and CPU overload."""

    def __init__(self, min_interval: float = 0.2):
        self.min_interval = min_interval
        self.last_update = 0.0
        self.pending_update: Optional[Tuple[Any, Callable]] = None
        self.lock = threading.Lock()

    def request_update(self, data: Any, callback: Callable, force: bool = False):
        """Receives an update request and throttles according to min_interval."""
        current_time = time.time()
        self.pending_update = (data, callback)

        if force or (current_time - self.last_update) >= self.min_interval:
            self._perform_update()

    def _perform_update(self):
        """Executes the pending callback if present."""
        if self.pending_update is not None:
            data, callback = self.pending_update
            callback(data)
            self.pending_update = None
            self.last_update = time.time()
