# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
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

# File: src/rendering/render_buffer_manager.py
# Author: Gabriel Moraes
# Date: September 2026

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
