# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Tuple


class MapViewportManager:
    """
    Manages layout dimensions and chrome offsets for the Map Viewport.
    """

    def __init__(self, chrome_width_offset: int = 330, chrome_height_offset: int = 140):
        self.chrome_width_offset = chrome_width_offset
        self.chrome_height_offset = chrome_height_offset
        self.width: int = 1280
        self.height: int = 720

    def calculate_dimensions(self, page_width: float | None, page_height: float | None) -> Tuple[int, int]:
        """Calculates canvas dimensions from the current page size."""
        pw = page_width or 1280
        ph = page_height or 800
        self.width = max(int(pw - self.chrome_width_offset), 400)
        self.height = max(int(ph - self.chrome_height_offset), 300)
        return self.width, self.height
