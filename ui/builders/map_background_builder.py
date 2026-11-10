# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Constructs the Flet background control for the LiveCanvasMapWidget stack,
aligning the CartoDB Positron basemap with MapDrawer coordinate transformations.
Follows Single Responsibility Principle (SRP).
"""

import base64
import logging
import os
from typing import Any, Optional

import flet as ft


class MapBackgroundBuilder:
    """
    Creates an ft.Container wrapping the basemap image, precisely dimensioned
    and positioned to sit underneath the Canvas.
    """

    # Feature toggle: disabled until further notice per user request (reactivatable via env CARINA_ENABLE_BASEMAP=1 or class attribute)
    ENABLED: bool = os.getenv("CARINA_ENABLE_BASEMAP", "0").lower() in ("1", "true", "yes")

    @classmethod
    def build(cls, basemap_path: Optional[str], drawer: Any, enabled: Optional[bool] = None) -> Optional[ft.Control]:
        """
        Builds the background control aligned with drawer transformations.

        Args:
            basemap_path: Absolute path to the basemap PNG image.
            drawer: MapDrawer instance with nodes, edges, and transform_point.
            enabled: Explicit override for feature flag (defaults to cls.ENABLED).

        Returns:
            An ft.Container control or None if basemap is not available or disabled.
        """
        is_enabled = cls.ENABLED if enabled is None else enabled
        if not is_enabled:
            return None

        if not basemap_path or not os.path.exists(basemap_path) or not drawer:
            return None

        try:
            min_x, max_x, min_y, max_y = None, None, None, None

            # 1. Check for exact alignment metadata JSON saved alongside the basemap
            base_name, _ = os.path.splitext(basemap_path)
            meta_path = f"{base_name}.json"
            if os.path.exists(meta_path):
                try:
                    import json

                    with open(meta_path, "r", encoding="utf-8") as f_meta:
                        meta = json.load(f_meta)
                        min_x = meta.get("min_x")
                        max_x = meta.get("max_x")
                        min_y = meta.get("min_y")
                        max_y = meta.get("max_y")
                except Exception as meta_err:
                    logging.debug(f"[MapBackgroundBuilder] Erro ao carregar metadados do basemap: {meta_err}")

            # 2. Fallback to drawer nodes and edges if metadata is unavailable
            if min_x is None or max_x is None or min_y is None or max_y is None:
                nodes = getattr(drawer, "nodes", {})
                edges = getattr(drawer, "edges", [])

                if isinstance(nodes, dict):
                    all_x = [n["x"] for n in nodes.values() if "x" in n]
                    all_y = [n["y"] for n in nodes.values() if "y" in n]
                elif isinstance(nodes, list):
                    all_x = [n["x"] for n in nodes if "x" in n]
                    all_y = [n["y"] for n in nodes if "y" in n]
                else:
                    all_x, all_y = [], []

                for e in edges:
                    shape = e.get("shape")
                    if shape:
                        for pt in shape:
                            all_x.append(pt[0])
                            all_y.append(pt[1])

                if not all_x or not all_y:
                    return None

                min_x, max_x = min(all_x), max(all_x)
                min_y, max_y = min(all_y), max(all_y)

            # In Flet Canvas, top-left is (min_x, max_y) and bottom-right is (max_x, min_y)
            top_left_x, top_left_y = drawer.transform_point(min_x, max_y)
            bottom_right_x, bottom_right_y = drawer.transform_point(max_x, min_y)

            width = max(1.0, bottom_right_x - top_left_x)
            height = max(1.0, bottom_right_y - top_left_y)

            # Read image as base64 to ensure immediate reliable rendering
            with open(basemap_path, "rb") as f:
                b64_data = base64.b64encode(f.read()).decode("utf-8")

            bg_image = ft.Image(
                src_base64=b64_data,
                fit=ft.ImageFit.FILL,
                width=width,
                height=height,
                opacity=1.0,
            )

            container = ft.Container(
                content=bg_image,
                left=top_left_x,
                top=top_left_y,
                width=width,
                height=height,
            )

            logging.info(
                f"[MapBackgroundBuilder] Controle de basemap criado: pos=({top_left_x:.1f}, {top_left_y:.1f}) tam=({width:.1f}x{height:.1f})"
            )
            return container
        except Exception as e:
            logging.warning(f"[MapBackgroundBuilder] Erro ao construir controle de basemap: {e}", exc_info=True)
            return None
