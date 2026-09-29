# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# File: src/rendering/static_map_renderer.py
# Author: Gabriel Moraes
# Date: September 2026

import logging
import os
import sys
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

project_root_render = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path_render = os.path.join(project_root_render, "src")
if src_path_render not in sys.path:
    sys.path.insert(0, src_path_render)

from rendering.static_map_painter import StaticMapPainter
from rendering.static_map_projector import StaticMapProjector
from src.utils.paths import resource_path
from utils.map_data_parser import parse_map_data
from utils.map_generator import generate_map_data_files

if TYPE_CHECKING:
    from src.utils.locale_manager_backend import LocaleManagerBackend

import matplotlib.pyplot as plt


class StaticMapRenderer:
    """
    Orchestrates the generation, parsing, and rendering of static maps and their associated assets.
    Delegates projection to StaticMapProjector and drawing to StaticMapPainter (Clean Architecture).
    """

    def __init__(self, locale_manager: "LocaleManagerBackend"):
        self.locale_manager = locale_manager
        self.icon_paths = {
            "existing": resource_path(os.path.join("ui", "assets", "icon_existing.png")),
            "add": resource_path(os.path.join("ui", "assets", "icon_add.png")),
            "remove": resource_path(os.path.join("ui", "assets", "icon_remove.png")),
        }
        logging.info(self.locale_manager.get_string("static_map_renderer.init.created"))

    def _draw_map_and_icons_with_matplotlib(
        self, nodes: Dict[str, Any], edges: List[Dict[str, Any]], bounds: Any, icon_requests: dict, output_path: str
    ) -> None:
        lm = self.locale_manager
        logging.info(lm.get_string("static_map_renderer.run.rendering_map", path=output_path))

        fig, ax = plt.subplots(figsize=(12, 8), dpi=100)

        # Coordinate projection
        projector = StaticMapProjector(base_width=1200.0, base_height=800.0)
        projector.compute_bounds_and_scale(nodes, edges)

        # Draw streets
        StaticMapPainter.draw_streets(ax, edges, projector.map_to_canvas)

        # Draw nodes and traffic light icons
        StaticMapPainter.draw_nodes_and_traffic_lights(ax, nodes, icon_requests, projector.map_to_canvas)

        # Chart style settings and limits
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_visible(False)
        ax.spines["left"].set_visible(False)
        ax.get_xaxis().set_ticks([])
        ax.get_yaxis().set_ticks([])
        ax.set_facecolor("#F7F7F7")

        ax.set_xlim(0, 1200)
        ax.set_ylim(0, 800)
        plt.subplots_adjust(left=0.0, right=1.0, bottom=0.0, top=1.0)

        try:
            plt.savefig(
                output_path, format="png", dpi=100, facecolor=ax.get_facecolor(), bbox_inches=None, pad_inches=0.0
            )
        except MemoryError as me:
            logging.critical(f"MemoryError ao salvar a imagem '{output_path}'.")
            raise me
        except Exception as save_err:
            logging.error(f"Erro inesperado ao salvar a imagem '{output_path}': {save_err}")
            raise save_err
        finally:
            plt.close(fig)

        logging.info(lm.get_string("static_map_renderer.run.render_complete", filename=os.path.basename(output_path)))

    def create_map_with_icons(
        self, net_file_path: str, scenario_results_dir: str, icon_requests: dict, output_filename: str
    ) -> Tuple[Optional[str], Optional[Tuple]]:
        """Orchestrates generation of static map with recommendation icons."""
        lm = self.locale_manager
        plain_xml_prefix = None
        try:
            maps_output_dir = os.path.join(scenario_results_dir, "maps")
            os.makedirs(maps_output_dir, exist_ok=True)

            plain_xml_prefix = generate_map_data_files(
                net_file_path=net_file_path, output_dir=scenario_results_dir, lm=self.locale_manager
            )

            if not plain_xml_prefix:
                logging.error("Falha ao gerar arquivos de dados do mapa. Prefixo plain XML não retornado.")
                return None, None

            map_data = parse_map_data(plain_xml_prefix)
            if not map_data:
                logging.error("Falha ao parsear os dados do mapa a partir dos arquivos XML.")
                return None, None

            nodes, edges, bounds = map_data
            if not nodes:
                logging.error("Nenhum nó encontrado nos dados do mapa parseados.")
                return None, None

            final_image_path = os.path.join(maps_output_dir, output_filename)
            self._draw_map_and_icons_with_matplotlib(nodes, edges, bounds, icon_requests, final_image_path)

            return final_image_path, (nodes, edges)
        except MemoryError:
            logging.critical("Falha ao gerar mapa devido a erro de memória (RAM). Verifique o log anterior.")
            return None, None
        except Exception as e:
            logging.error(lm.get_string("static_map_renderer.run.critical_error_icons", error=e), exc_info=True)
            return None, None
        finally:
            if plain_xml_prefix:
                try:
                    if os.path.exists(plain_xml_prefix + ".nod.xml"):
                        os.remove(plain_xml_prefix + ".nod.xml")
                    if os.path.exists(plain_xml_prefix + ".edg.xml"):
                        os.remove(plain_xml_prefix + ".edg.xml")
                except Exception as cleanup_err:
                    logging.warning(f"Erro ao limpar arquivos XML temporários: {cleanup_err}")

    def generate_coordinates_file(
        self,
        map_data: tuple,
        traffic_light_ids: list,
        scenario_results_dir: str,
        image_width: int = 3840,
        image_height: int = 2160,
    ) -> Optional[str]:
        """Delegates the coordinates data file generation to MapCoordinateGenerator."""
        from rendering.map_coordinate_generator import MapCoordinateGenerator

        generator = MapCoordinateGenerator(self.locale_manager)
        return generator.generate_coordinates_file(
            map_data=map_data,
            traffic_light_ids=traffic_light_ids,
            scenario_results_dir=scenario_results_dir,
            image_width=image_width,
            image_height=image_height,
        )
