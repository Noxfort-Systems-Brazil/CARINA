# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import io
import logging
from typing import Tuple

import requests
from PIL import Image, ImageEnhance


class BasemapTileClient:
    """Handles HTTP downloading of map tiles (Esri Canvas Base & Reference, OSM) and grid compositing."""

    USER_AGENT = "CARINA-Urban-Traffic/1.2 (Noxfort Systems; Adaptive Traffic Control)"

    @classmethod
    def fetch_and_stitch_tiles(
        cls,
        zoom: int,
        x_start: int,
        x_end: int,
        y_start: int,
        y_end: int,
    ) -> Tuple[Image.Image, int]:
        """
        Downloads and stitches tiles across the requested tile coordinates grid.
        Returns the stitched PIL image (harmonized) and the number of downloaded tiles.
        """
        num_tiles_x = x_end - x_start + 1
        num_tiles_y = y_end - y_start + 1
        grid_width = num_tiles_x * 256
        grid_height = num_tiles_y * 256
        composite_image = Image.new("RGB", (grid_width, grid_height), color=(247, 247, 247))

        session = requests.Session()
        session.headers.update({"User-Agent": cls.USER_AGENT})
        downloaded_count = 0

        for xi, tx in enumerate(range(x_start, x_end + 1)):
            for yi, ty in enumerate(range(y_start, y_end + 1)):
                url_base = f"https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{zoom}/{ty}/{tx}"
                url_ref = f"https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Reference/MapServer/tile/{zoom}/{ty}/{tx}"

                try:
                    resp_base = session.get(url_base, timeout=4.0)
                    if resp_base.status_code == 200:
                        tile_base = Image.open(io.BytesIO(resp_base.content)).convert("RGBA")
                        try:
                            resp_ref = session.get(url_ref, timeout=3.0)
                            if resp_ref.status_code == 200:
                                tile_ref = Image.open(io.BytesIO(resp_ref.content)).convert("RGBA")
                                tile_base = Image.alpha_composite(tile_base, tile_ref)
                        except Exception:
                            pass

                        composite_image.paste(tile_base.convert("RGB"), (xi * 256, yi * 256))
                        downloaded_count += 1
                    else:
                        fallback_url = f"https://tile.openstreetmap.org/{zoom}/{tx}/{ty}.png"
                        resp_fb = session.get(fallback_url, timeout=3.0)
                        if resp_fb.status_code == 200:
                            fb_img = Image.open(io.BytesIO(resp_fb.content)).convert("RGB")
                            composite_image.paste(fb_img, (xi * 256, yi * 256))
                            downloaded_count += 1
                except Exception as req_err:
                    logging.warning(f"[BasemapTileClient] Falha ao baixar tile ({tx}, {ty}): {req_err}", exc_info=True)

        if downloaded_count > 0:
            # Harmonize background luminosity with CARINA's #F7F7F7
            enhancer = ImageEnhance.Brightness(composite_image)
            composite_image = enhancer.enhance(247.0 / 239.0)

        return composite_image, downloaded_count
