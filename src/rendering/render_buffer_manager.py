# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import threading
from typing import Any, List, Optional


class RenderBufferManager:
    """Thread-safe double buffer manager for smooth visual rendering."""

    def __init__(self, buffer_count: int = 2):
        self.buffers: List[Optional[Any]] = [None] * buffer_count
        self.current_write_idx = 0
        self.current_read_idx = 1
        self.lock = threading.Lock()

    def write_buffer(self, data: Any) -> None:
        """Writes data to the current write buffer and swaps read/write indices."""
        with self.lock:
            self.buffers[self.current_write_idx] = data
            self.current_write_idx, self.current_read_idx = (
                self.current_read_idx,
                self.current_write_idx,
            )

    def read_buffer(self) -> Any:
        """Reads data from the current read buffer."""
        with self.lock:
            return self.buffers[self.current_read_idx]
