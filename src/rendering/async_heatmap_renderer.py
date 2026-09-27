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

# File: src/rendering/async_heatmap_renderer.py
# Author: Gabriel Moraes
# Date: April 23, 2026

import base64
import io
import logging
import queue
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Callable, Optional, Tuple

import matplotlib.pyplot as plt

from src.rendering.congestion_color_scheme import CongestionColorScheme
from src.rendering.render_buffer_manager import RenderBufferManager
from src.rendering.update_throttler import UpdateThrottler

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

# Re-exports for backward compatibility
__all__ = ["AsyncHeatmapRenderer", "UpdateThrottler", "RenderBufferManager", "CongestionColorScheme"]


class AsyncHeatmapRenderer:
    """Asynchronous heatmap renderer to avoid interface freezing."""

    def __init__(self, locale_manager: "LocaleManagerBackend"):
        """Initializes the asynchronous heatmap renderer."""
        self.locale_manager = locale_manager
        self.executor = ThreadPoolExecutor(max_workers=2)  # 2 workers for rendering
        self.render_queue = queue.Queue()
        self.result_cache = {}
        self.cache_size_limit = 10  # Cache limit to avoid excessive memory consumption

        logging.info(self.locale_manager.get_string("async_heatmap_renderer.init.created"))

    def create_heatmap_image_in_memory_async(
        self,
        map_data: tuple,
        congestion_data: dict,
        saturation_threshold: float = 100.0,
        callback: Optional[Callable[[Optional[str]], None]] = None,
    ):
        """
        Gera uma imagem de mapa com as ruas coloridas pelo nível de
        congestionamento de forma assíncrona e chama o callback com o resultado.
        """
        future = self.executor.submit(
            self._create_heatmap_internal,
            map_data,
            congestion_data,
            saturation_threshold,
        )

        if callback:

            def handle_result(fut):
                try:
                    result = fut.result()
                    callback(result)
                except Exception as e:
                    logging.error(f"Erro no callback do heatmap: {e}")
                    callback(None)

            future.add_done_callback(handle_result)

    def get_precise_color_for_congestion(
        self, value: float, max_expected_value: float = 100.0
    ) -> Tuple[float, float, float]:
        """Converte um valor de congestão em uma tupla RGB com alta precisão."""
        return CongestionColorScheme.get_precise_color_for_congestion(value, max_expected_value)

    def get_enhanced_color_for_congestion(
        self, value: float, max_expected_value: float = 100.0
    ) -> Tuple[float, float, float]:
        """Converte um valor de congestão em uma tupla RGB com escala avançada."""
        return CongestionColorScheme.get_enhanced_color_for_congestion(value, max_expected_value)

    def _create_heatmap_internal(
        self,
        map_data: tuple,
        congestion_data: dict,
        saturation_threshold: float,
    ) -> Optional[str]:
        """Método interno que realiza a renderização do heatmap fora da thread UI."""
        lm = self.locale_manager
        try:
            nodes, edges = map_data
            fig, ax = plt.subplots(figsize=(4.8, 2.88), dpi=100)

            threshold = max(saturation_threshold, 1.0)

            for edge in edges:
                edge_id = edge.get("id", "")
                congestion_index = congestion_data.get(edge_id, 0.0)
                color = self.get_enhanced_color_for_congestion(congestion_index, threshold)

                shape = edge["shape"]
                x_coords, y_coords = zip(*shape)

                ax.plot(
                    x_coords,
                    y_coords,
                    color=color,
                    linewidth=2.0,
                    zorder=1,
                    solid_capstyle="round",
                )

            if nodes:
                node_x = [n["x"] for n in nodes.values()]
                node_y = [n["y"] for n in nodes.values()]
                ax.scatter(node_x, node_y, s=10, color="#808080", zorder=2)

            ax.set_aspect("equal", adjustable="box")
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.spines["bottom"].set_visible(False)
            ax.spines["left"].set_visible(False)
            ax.get_xaxis().set_ticks([])
            ax.get_yaxis().set_ticks([])
            ax.set_facecolor("#F7F7F7")

            buf = io.BytesIO()
            plt.savefig(
                buf,
                format="png",
                dpi=100,
                facecolor=ax.get_facecolor(),
                bbox_inches="tight",
                pad_inches=0.05,
            )
            plt.close(fig)
            buf.seek(0)

            image_base64 = base64.b64encode(buf.read()).decode("utf-8")
            return image_base64

        except Exception as e:
            logging.error(lm.get_string("async_heatmap_renderer.run.error", error=e), exc_info=True)
            return None

    def shutdown(self):
        """Encerra o executor e libera recursos."""
        self.executor.shutdown(wait=True)
