# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

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
