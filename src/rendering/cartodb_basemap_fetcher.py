# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Fetches, stitches, and crops professional CCO basemap tiles (Esri World Light Gray Canvas)
for a given geographic bounding box (WGS84). Coordinates math is delegated to BasemapGeoMath
and tile downloading is delegated to BasemapTileClient.
"""

import json
import logging
import os
import shutil
from typing import Optional, Tuple

from PIL import Image

from src.rendering.basemap_geo_math import BasemapGeoMath
from src.rendering.basemap_tile_client import BasemapTileClient
from src.utils.sumo_geo_bounds_reader import SumoGeoBounds


class CartoDBBasemapFetcher:
    """Specialist facade responsible for generating an aligned CCO basemap image with contextual padding."""

    SUBDOMAINS = ["a", "b", "c", "d"]
    USER_AGENT = BasemapTileClient.USER_AGENT
    DEFAULT_FILENAME = "basemap_positron.png"
    BACKUP_FILENAME = "basemap_backup.png"
    METADATA_EXT = ".json"
    DEFAULT_PADDING_RATIO = BasemapGeoMath.DEFAULT_PADDING_RATIO
    ENABLED: bool = os.getenv("CARINA_ENABLE_BASEMAP", "0").lower() in ("1", "true", "yes")

    # Delegate geometric calculations for backward compatibility
    _compute_padded_bounds = staticmethod(BasemapGeoMath.compute_padded_bounds)
    _lon_lat_to_tile = staticmethod(BasemapGeoMath.lon_lat_to_tile)
    _lon_lat_to_pixel = staticmethod(BasemapGeoMath.lon_lat_to_pixel)
    _compute_best_zoom = staticmethod(BasemapGeoMath.compute_best_zoom)

    @classmethod
    def fetch_basemap(
        cls,
        bounds: SumoGeoBounds,
        output_dir: str,
        filename: str = DEFAULT_FILENAME,
        style: str = "light_all",
        padding_ratio: float = DEFAULT_PADDING_RATIO,
        force_refresh: bool = False,
        enabled: Optional[bool] = None,
    ) -> Optional[str]:
        """Fetches, stitches, blends, and saves an Esri Light Gray Canvas basemap with contextual padding."""
        is_enabled = cls.ENABLED if enabled is None else enabled
        if not is_enabled:
            logging.debug("[BasemapFetcher] Geração de basemap desativada (ENABLED=False).")
            return None

        if not bounds.has_geo_coords:
            logging.info("[BasemapFetcher] A malha SUMO não possui coordenadas geográficas (WGS84). Basemap ignorado.")
            return None

        os.makedirs(output_dir, exist_ok=True)
        final_image_path = os.path.join(output_dir, filename)
        base_name, _ = os.path.splitext(filename)
        meta_image_path = os.path.join(output_dir, f"{base_name}{cls.METADATA_EXT}")

        backup_image_path = os.path.join(output_dir, cls.BACKUP_FILENAME)
        backup_base_name, _ = os.path.splitext(cls.BACKUP_FILENAME)
        backup_meta_path = os.path.join(output_dir, f"{backup_base_name}{cls.METADATA_EXT}")

        def _try_fallback_to_backup() -> Optional[str]:
            if os.path.exists(backup_image_path) and os.path.getsize(backup_image_path) > 0:
                logging.info(f"[BasemapFetcher] Recuperando basemap a partir do backup: {backup_image_path}")
                try:
                    if final_image_path != backup_image_path:
                        shutil.copy2(backup_image_path, final_image_path)
                    if os.path.exists(backup_meta_path) and meta_image_path != backup_meta_path:
                        shutil.copy2(backup_meta_path, meta_image_path)
                    return final_image_path
                except Exception as cp_err:
                    logging.warning(f"[BasemapFetcher] Falha ao restaurar backup: {cp_err}", exc_info=True)
            return None

        # 1. Offline Cache Check
        if (
            not force_refresh
            and os.path.exists(final_image_path)
            and os.path.getsize(final_image_path) > 0
            and os.path.exists(meta_image_path)
        ):
            logging.info(f"[BasemapFetcher] Basemap encontrado em cache: {final_image_path}")
            if not os.path.exists(backup_image_path) or os.path.getsize(backup_image_path) == 0:
                try:
                    shutil.copy2(final_image_path, backup_image_path)
                    if os.path.exists(meta_image_path):
                        shutil.copy2(meta_image_path, backup_meta_path)
                except Exception:
                    pass
            return final_image_path

        try:
            # 2. Compute Padded Geographic Bounds
            (
                p_min_x,
                p_max_x,
                p_min_y,
                p_max_y,
                p_min_lon,
                p_max_lon,
                p_min_lat,
                p_max_lat,
            ) = BasemapGeoMath.compute_padded_bounds(bounds, padding_ratio=padding_ratio)

            # 3. Determine Zoom & Tile Grid
            zoom = BasemapGeoMath.compute_best_zoom(p_min_lon, p_max_lon)
            x0, y0 = BasemapGeoMath.lon_lat_to_tile(p_min_lon, p_max_lat, zoom)
            x1, y1 = BasemapGeoMath.lon_lat_to_tile(p_max_lon, p_min_lat, zoom)

            x_start, x_end = min(x0, x1), max(x0, x1)
            y_start, y_end = min(y0, y1), max(y0, y1)
            num_tiles_x = x_end - x_start + 1
            num_tiles_y = y_end - y_start + 1

            while num_tiles_x * num_tiles_y > 25 and zoom > 12:
                zoom -= 1
                x0, y0 = BasemapGeoMath.lon_lat_to_tile(p_min_lon, p_max_lat, zoom)
                x1, y1 = BasemapGeoMath.lon_lat_to_tile(p_max_lon, p_min_lat, zoom)
                x_start, x_end = min(x0, x1), max(x0, x1)
                y_start, y_end = min(y0, y1), max(y0, y1)
                num_tiles_x = x_end - x_start + 1
                num_tiles_y = y_end - y_start + 1

            logging.info(
                f"[BasemapFetcher] Baixando tiles Esri Canvas | Zoom: {zoom} | Grade: {num_tiles_x}x{num_tiles_y}"
            )

            # 4. Download & Stitch Tiles
            composite_image, downloaded_count = BasemapTileClient.fetch_and_stitch_tiles(
                zoom, x_start, x_end, y_start, y_end
            )

            if downloaded_count == 0:
                logging.warning("[BasemapFetcher] Nenhum tile pôde ser baixado (offline). Verificando backup...")
                backup_res = _try_fallback_to_backup()
                return backup_res

            # 5. Precise Crop to Padded Bounds in Web Mercator
            grid_width = num_tiles_x * 256
            grid_height = num_tiles_y * 256
            px_left, py_top = BasemapGeoMath.lon_lat_to_pixel(p_min_lon, p_max_lat, zoom, x_start, y_start)
            px_right, py_bottom = BasemapGeoMath.lon_lat_to_pixel(p_max_lon, p_min_lat, zoom, x_start, y_start)

            c_left = max(0.0, min(px_left, px_right))
            c_top = max(0.0, min(py_top, py_bottom))
            c_right = min(float(grid_width), max(px_left, px_right))
            c_bottom = min(float(grid_height), max(py_top, py_bottom))

            if c_right > c_left + 10 and c_bottom > c_top + 10:
                final_cropped = composite_image.crop((int(c_left), int(c_top), int(c_right), int(c_bottom)))
            else:
                final_cropped = composite_image

            final_cropped.save(final_image_path, "PNG", optimize=True)

            # 6. Save Alignment Metadata JSON
            meta = {
                "min_x": round(p_min_x, 3),
                "max_x": round(p_max_x, 3),
                "min_y": round(p_min_y, 3),
                "max_y": round(p_max_y, 3),
                "min_lon": p_min_lon,
                "max_lon": p_max_lon,
                "min_lat": p_min_lat,
                "max_lat": p_max_lat,
                "width": final_cropped.width,
                "height": final_cropped.height,
                "padding_ratio": padding_ratio,
            }
            with open(meta_image_path, "w", encoding="utf-8") as f_meta:
                json.dump(meta, f_meta, indent=2)

            # 7. Update Persistent Backup Copies
            try:
                shutil.copy2(final_image_path, backup_image_path)
                shutil.copy2(meta_image_path, backup_meta_path)
            except Exception as bkp_err:
                logging.debug(f"[BasemapFetcher] Não foi possível atualizar backup: {bkp_err}")

            return final_image_path

        except Exception as e:
            logging.error(f"[BasemapFetcher] Erro durante processamento do basemap: {e}", exc_info=True)
            return _try_fallback_to_backup()
