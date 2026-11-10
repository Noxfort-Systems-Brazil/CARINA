# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import tempfile
from unittest.mock import MagicMock
import pytest
from PIL import Image

from src.rendering.static_map_background_painter import StaticMapBackgroundPainter
from src.rendering.static_map_projector import StaticMapProjector


def test_apply_background_disabled_by_default():
    ax_mock = MagicMock()
    projector = StaticMapProjector(1200, 800)
    with tempfile.TemporaryDirectory() as tmp_dir:
        img_path = os.path.join(tmp_dir, "test_basemap.png")
        img = Image.new("RGB", (200, 200), color=(250, 250, 250))
        img.save(img_path)
        # By default (disabled), must return False and not call imshow
        applied = StaticMapBackgroundPainter.apply_background(ax_mock, img_path, projector)
        assert applied is False
        ax_mock.imshow.assert_not_called()


def test_apply_background_missing_file():
    ax_mock = MagicMock()
    projector = StaticMapProjector(1200, 800)
    applied = StaticMapBackgroundPainter.apply_background(ax_mock, "/non/existent/img.png", projector, enabled=True)
    assert applied is False
    ax_mock.imshow.assert_not_called()


def test_apply_background_valid_file():
    with tempfile.TemporaryDirectory() as tmp_dir:
        img_path = os.path.join(tmp_dir, "test_basemap.png")
        img = Image.new("RGB", (200, 200), color=(250, 250, 250))
        img.save(img_path)

        ax_mock = MagicMock()
        projector = StaticMapProjector(1200, 800)
        projector.min_x = 0
        projector.max_x = 1000
        projector.min_y = 0
        projector.max_y = 800
        projector.fit_scale = 1.0

        applied = StaticMapBackgroundPainter.apply_background(ax_mock, img_path, projector, enabled=True)
        assert applied is True
        ax_mock.imshow.assert_called_once()


def test_apply_background_with_metadata():
    import json

    with tempfile.TemporaryDirectory() as tmp_dir:
        img_path = os.path.join(tmp_dir, "test_basemap.png")
        meta_path = os.path.join(tmp_dir, "test_basemap.json")
        img = Image.new("RGB", (200, 200), color=(250, 250, 250))
        img.save(img_path)

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump({"min_x": -100.0, "max_x": 1100.0, "min_y": -100.0, "max_y": 900.0}, f)

        ax_mock = MagicMock()
        projector = StaticMapProjector(1200, 800)
        projector.map_to_canvas = MagicMock(side_effect=lambda x, y: (x + 10.0, y + 10.0))

        applied = StaticMapBackgroundPainter.apply_background(ax_mock, img_path, projector, enabled=True)
        assert applied is True
        ax_mock.imshow.assert_called_once()
        _, kwargs = ax_mock.imshow.call_args
        # extent should be [cx_min, cx_max, cy_min, cy_max] = [-90.0, 1110.0, -90.0, 910.0]
        assert kwargs["extent"] == [-90.0, 1110.0, -90.0, 910.0]
