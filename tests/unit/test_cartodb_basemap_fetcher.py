# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import io
import os
import tempfile
from unittest.mock import MagicMock, patch
import pytest
from PIL import Image

from src.rendering.cartodb_basemap_fetcher import CartoDBBasemapFetcher
from src.utils.sumo_geo_bounds_reader import SumoGeoBounds


def test_lon_lat_to_tile_conversion():
    # Greenwich (lon=0, lat=0) at zoom 0 is (0, 0)
    tx, ty = CartoDBBasemapFetcher._lon_lat_to_tile(0.0, 0.0, 0)
    assert tx == 0
    assert ty == 0

    # São Paulo approximate coordinates at zoom 15
    tx_sp, ty_sp = CartoDBBasemapFetcher._lon_lat_to_tile(-46.65, -23.56, 15)
    assert tx_sp > 0
    assert ty_sp > 0


def test_compute_best_zoom():
    # City-scale span: ~0.05 degrees longitude
    zoom = CartoDBBasemapFetcher._compute_best_zoom(-46.70, -46.60)
    assert 13 <= zoom <= 18


def test_fetch_basemap_disabled_by_default():
    bounds = SumoGeoBounds(
        min_lon=-46.65,
        min_lat=-23.56,
        max_lon=-46.64,
        max_lat=-23.55,
        min_x=0.0,
        min_y=0.0,
        max_x=1000.0,
        max_y=1000.0,
    )
    with tempfile.TemporaryDirectory() as tmp_dir:
        # When disabled (default), returns None immediately
        result = CartoDBBasemapFetcher.fetch_basemap(bounds, tmp_dir)
        assert result is None


def test_fetch_basemap_offline_cache():
    import json

    bounds = SumoGeoBounds(
        min_lon=-46.65,
        min_lat=-23.56,
        max_lon=-46.64,
        max_lat=-23.55,
        min_x=0.0,
        min_y=0.0,
        max_x=1000.0,
        max_y=1000.0,
    )
    with tempfile.TemporaryDirectory() as tmp_dir:
        cached_file = os.path.join(tmp_dir, "basemap_positron.png")
        cached_meta = os.path.join(tmp_dir, "basemap_positron.json")
        # Create a dummy cached file and metadata
        img = Image.new("RGB", (100, 100), color=(200, 200, 200))
        img.save(cached_file)
        with open(cached_meta, "w") as f:
            json.dump({"min_x": 0.0, "max_x": 1000.0, "min_y": 0.0, "max_y": 1000.0}, f)

        # Should immediately return cached path without making any network requests when enabled
        result = CartoDBBasemapFetcher.fetch_basemap(bounds, tmp_dir, enabled=True)
        assert result == cached_file


def test_fetch_basemap_download_with_mock():
    bounds = SumoGeoBounds(
        min_lon=-46.65,
        min_lat=-23.56,
        max_lon=-46.649,
        max_lat=-23.559,
        min_x=0.0,
        min_y=0.0,
        max_x=100.0,
        max_y=100.0,
    )
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create a 256x256 test PNG tile in memory
        tile_img = Image.new("RGB", (256, 256), color=(240, 240, 240))
        buf = io.BytesIO()
        tile_img.save(buf, format="PNG")
        mock_tile_bytes = buf.getvalue()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = mock_tile_bytes

        with patch("requests.Session.get", return_value=mock_resp):
            result = CartoDBBasemapFetcher.fetch_basemap(bounds, tmp_dir, force_refresh=True, enabled=True)
            assert result is not None
            assert os.path.exists(result)
            loaded = Image.open(result)
            assert loaded.size[0] > 0
            assert loaded.size[1] > 0

            # Verify that backup file was automatically created
            backup_path = os.path.join(tmp_dir, "basemap_backup.png")
            assert os.path.exists(backup_path)
            assert os.path.getsize(backup_path) > 0


def test_fetch_basemap_fallback_to_backup_on_error():
    bounds = SumoGeoBounds(
        min_lon=-46.65,
        min_lat=-23.56,
        max_lon=-46.649,
        max_lat=-23.559,
        min_x=0.0,
        min_y=0.0,
        max_x=100.0,
        max_y=100.0,
    )
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Pre-seed a backup file
        backup_path = os.path.join(tmp_dir, "basemap_backup.png")
        backup_img = Image.new("RGB", (120, 120), color=(180, 180, 180))
        backup_img.save(backup_path)

        # Simulate network failure (e.g. timeout / connection error)
        with patch("requests.Session.get", side_effect=OSError("Connection refused / Offline")):
            result = CartoDBBasemapFetcher.fetch_basemap(bounds, tmp_dir, force_refresh=True, enabled=True)
            # Should have recovered from backup!
            assert result is not None
            assert os.path.exists(result)
            restored = Image.open(result)
            assert restored.size == (120, 120)

