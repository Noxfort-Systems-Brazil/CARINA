# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Applies a CartoDB Positron basemap image as the background of a Matplotlib Axes object.
Calculates extent and coordinate alignment using StaticMapProjector.
Follows Single Responsibility Principle (SRP).
"""

import logging
import os
from typing import Any, Optional

import matplotlib.pyplot as plt
from matplotlib.axes import Axes


class StaticMapBackgroundPainter:
    """
    Renders the background basemap onto a Matplotlib Axes in exact alignment
    with SUMO network coordinates.
    """

    # Feature toggle: disabled until further notice per user request (can be re-enabled via CARINA_ENABLE_BASEMAP=1 env or class attribute)
    ENABLED: bool = os.getenv("CARINA_ENABLE_BASEMAP", "0").lower() in ("1", "true", "yes")

    @classmethod
    def apply_background(
        cls, ax: Axes, basemap_path: Optional[str], projector: Any, alpha: float = 0.95, enabled: Optional[bool] = None
    ) -> bool:
        """
        Draws the basemap onto the given matplotlib axes using the projection geometry.

        Args:
            ax: The matplotlib Axes object.
            basemap_path: Path to the PNG basemap image on disk.
            projector: StaticMapProjector instance with computed bounds.
            alpha: Opacity of the background image (default 0.95).
            enabled: Explicit override for feature flag (defaults to cls.ENABLED).

        Returns:
            True if background was applied, False otherwise.
        """
        is_enabled = cls.ENABLED if enabled is None else enabled
        if not is_enabled:
            return False

        if not basemap_path or not os.path.exists(basemap_path):
            return False

        try:
            import json

            img = plt.imread(basemap_path)

            min_x, max_x = projector.min_x, projector.max_x
            min_y, max_y = projector.min_y, projector.max_y

            # Check if alignment metadata JSON exists with exact padded bounds
            base_name, _ = os.path.splitext(basemap_path)
            meta_path = f"{base_name}.json"
            if os.path.exists(meta_path):
                try:
                    with open(meta_path, "r", encoding="utf-8") as f_meta:
                        meta = json.load(f_meta)
                        min_x = meta.get("min_x", min_x)
                        max_x = meta.get("max_x", max_x)
                        min_y = meta.get("min_y", min_y)
                        max_y = meta.get("max_y", max_y)
                except Exception as meta_err:
                    logging.debug(f"[StaticMapBackgroundPainter] Erro ao ler metadados do basemap: {meta_err}")

            # Map the network bounding box in meters to screen canvas pixels
            cx_min, cy_min = projector.map_to_canvas(min_x, min_y)
            cx_max, cy_max = projector.map_to_canvas(max_x, max_y)

            # In Matplotlib with ax.set_ylim(0, 800), cy increases upwards.
            # The top of the image corresponds to North (max_y -> cy_max),
            # while the bottom corresponds to South (min_y -> cy_min).
            extent = [cx_min, cx_max, cy_min, cy_max]

            ax.imshow(img, extent=extent, origin="upper", zorder=0, alpha=alpha, interpolation="bilinear")
            logging.info(f"[StaticMapBackgroundPainter] Basemap aplicado ao canvas Matplotlib: extent={extent}")
            return True
        except Exception as e:
            logging.warning(f"[StaticMapBackgroundPainter] Falha ao aplicar basemap no Matplotlib: {e}", exc_info=True)
            return False
