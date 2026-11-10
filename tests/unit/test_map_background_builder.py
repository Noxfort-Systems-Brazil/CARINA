# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import tempfile
from unittest.mock import MagicMock
import flet as ft
import pytest
from PIL import Image

from ui.builders.map_background_builder import MapBackgroundBuilder


def test_map_background_builder_disabled_by_default():
    drawer_mock = MagicMock()
    with tempfile.TemporaryDirectory() as tmp_dir:
        img_path = os.path.join(tmp_dir, "test_basemap.png")
        img = Image.new("RGB", (100, 100), color=(240, 240, 240))
        img.save(img_path)
        # By default (disabled), must return None
        result = MapBackgroundBuilder.build(img_path, drawer_mock)
        assert result is None


def test_map_background_builder_missing_file():
    drawer_mock = MagicMock()
    result = MapBackgroundBuilder.build("/non/existent/bg.png", drawer_mock, enabled=True)
    assert result is None


def test_map_background_builder_valid():
    with tempfile.TemporaryDirectory() as tmp_dir:
        img_path = os.path.join(tmp_dir, "test_basemap.png")
        img = Image.new("RGB", (100, 100), color=(240, 240, 240))
        img.save(img_path)

        drawer_mock = MagicMock()
        drawer_mock.nodes = {"n1": {"x": 10.0, "y": 20.0}, "n2": {"x": 100.0, "y": 200.0}}
        drawer_mock.edges = [{"shape": [(10.0, 20.0), (100.0, 200.0)]}]
        drawer_mock.transform_point.side_effect = lambda x, y: (x * 2.0, y * 2.0)

        container = MapBackgroundBuilder.build(img_path, drawer_mock, enabled=True)
        assert container is not None
        assert isinstance(container, ft.Container)
        assert isinstance(container.content, ft.Image)
        assert container.content.src_base64 is not None


def test_map_background_builder_with_metadata():
    import json

    with tempfile.TemporaryDirectory() as tmp_dir:
        img_path = os.path.join(tmp_dir, "test_basemap.png")
        meta_path = os.path.join(tmp_dir, "test_basemap.json")
        img = Image.new("RGB", (100, 100), color=(240, 240, 240))
        img.save(img_path)

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump({"min_x": -50.0, "max_x": 150.0, "min_y": -50.0, "max_y": 250.0}, f)

        drawer_mock = MagicMock()
        drawer_mock.transform_point.side_effect = lambda x, y: (x * 2.0, y * 2.0)

        container = MapBackgroundBuilder.build(img_path, drawer_mock, enabled=True)
        assert container is not None
        assert isinstance(container, ft.Container)
        # drawer.transform_point(-50, 250) -> (-100, 500)
        assert container.left == -100.0
        assert container.top == 500.0
