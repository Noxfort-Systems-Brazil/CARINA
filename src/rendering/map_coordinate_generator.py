# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.utils.locale_manager_backend import LocaleManagerBackend


class MapCoordinateGenerator:
    """Specialist responsible for generating standard pixel coordinates JSON for traffic light nodes."""

    def __init__(self, locale_manager: "LocaleManagerBackend"):
        self.locale_manager = locale_manager

    def generate_coordinates_file(
        self,
        map_data: tuple,
        traffic_light_ids: list,
        scenario_results_dir: str,
        image_width: int = 3840,
        image_height: int = 2160,
    ) -> str | None:
        lm = self.locale_manager
        try:
            if not isinstance(map_data, tuple) or len(map_data) != 2:
                logging.error("Dados do mapa inválidos para gerar coordenadas.")
                return None
            nodes, edges = map_data
            if not nodes or not edges:
                logging.error("Nós ou arestas ausentes nos dados do mapa para gerar coordenadas.")
                return None

            # Collects all x and y coordinates to find the limits
            all_x = [n["x"] for n in nodes.values() if "x" in n]
            all_y = [n["y"] for n in nodes.values() if "y" in n]
            for e in edges:
                if "shape" in e and e["shape"]:
                    try:
                        x_coords, y_coords = zip(*e["shape"])
                        all_x.extend(x_coords)
                        all_y.extend(y_coords)
                    except ValueError:
                        pass

            if not all_x or not all_y:
                logging.error("Não foi possível extrair coordenadas dos nós/arestas.")
                return None

            min_x, max_x = min(all_x), max(all_x)
            min_y, max_y = min(all_y), max(all_y)

            map_width = max_x - min_x
            map_height = max_y - min_y
            if map_width <= 0 or map_height <= 0:
                logging.warning(
                    f"Dimensões do mapa inválidas calculadas: W={map_width}, H={map_height}. Não é possível gerar coordenadas."
                )
                return None

            padding_ratio = (0.1 * 2) / 9.6
            padding = image_width * padding_ratio / 2
            view_width = image_width - (padding * 2)
            view_height = image_height - (padding * 2)

            # Calculates scale ensuring the map fits in the viewing area
            scale_x = view_width / map_width if map_width > 0 else 1
            scale_y = view_height / map_height if map_height > 0 else 1
            scale = min(scale_x, scale_y)

            # Calculates the width and height of the scaled map
            centered_map_width = map_width * scale
            centered_map_height = map_height * scale

            # Calculates offsets to center the map in the image
            offset_x = (image_width - centered_map_width) / 2 - (min_x * scale)
            offset_y_canvas_top = (image_height - centered_map_height) / 2
            offset_y = offset_y_canvas_top + (max_y * scale)

            coordinates = {}
            for tl_id in traffic_light_ids:
                if tl_id in nodes:
                    node = nodes[tl_id]
                    if "x" in node and "y" in node:
                        pixel_x = node["x"] * scale + offset_x
                        pixel_y = offset_y - (node["y"] * scale)
                        coordinates[tl_id] = {"x": round(pixel_x, 2), "y": round(pixel_y, 2)}
                    else:
                        logging.warning(f"Nó '{tl_id}' não possui coordenadas 'x' ou 'y'.")

            maps_output_dir = os.path.join(scenario_results_dir, "maps")
            os.makedirs(maps_output_dir, exist_ok=True)
            output_path = os.path.join(maps_output_dir, "map_coords.json")

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(coordinates, f, indent=4)

            return output_path
        except Exception as e:
            logging.error(lm.get_string("static_map_renderer.run.critical_error_coords", error=e), exc_info=True)
            return None
