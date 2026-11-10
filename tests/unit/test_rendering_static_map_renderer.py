# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
from unittest.mock import MagicMock, patch
import pytest

from src.rendering.static_map_renderer import StaticMapRenderer


@pytest.fixture
def renderer_fixture():
    lm = MagicMock()
    lm.get_string.side_effect = lambda k, **kw: f"mock_{k}"
    renderer = StaticMapRenderer(locale_manager=lm)
    return renderer, lm


def test_static_map_renderer_init(renderer_fixture):
    renderer, lm = renderer_fixture
    assert renderer.locale_manager is lm
    assert "existing" in renderer.icon_paths
    assert "add" in renderer.icon_paths
    assert "remove" in renderer.icon_paths


def test_static_map_renderer_draw_matplotlib(renderer_fixture, tmp_path):
    renderer, _ = renderer_fixture
    output_png = str(tmp_path / "map.png")

    nodes = {"n1": {"x": 10.0, "y": 20.0}}
    edges = [{"from": "n1", "to": "n1", "shape": [(10.0, 20.0), (30.0, 40.0)]}]
    bounds = (0.0, 0.0, 100.0, 100.0)

    with patch("src.rendering.static_map_painter.StaticMapPainter.draw_streets") as mock_streets, \
         patch("src.rendering.static_map_painter.StaticMapPainter.draw_nodes_and_traffic_lights") as mock_nodes, \
         patch("matplotlib.pyplot.savefig") as mock_savefig:

        renderer._draw_map_and_icons_with_matplotlib(
            nodes=nodes,
            edges=edges,
            bounds=bounds,
            icon_requests={},
            output_path=output_png,
            basemap_path=None,
        )

        assert mock_streets.called
        assert mock_nodes.called
        assert mock_savefig.called


def test_static_map_renderer_draw_matplotlib_with_basemap_and_error(renderer_fixture, tmp_path):
    renderer, _ = renderer_fixture
    output_png = str(tmp_path / "map_err.png")

    nodes = {"n1": {"x": 10.0, "y": 20.0}}
    edges = [{"from": "n1", "to": "n1", "shape": [(10.0, 20.0), (30.0, 40.0)]}]

    with patch("src.rendering.static_map_background_painter.StaticMapBackgroundPainter.apply_background") as mock_bg, \
         patch("matplotlib.pyplot.savefig", side_effect=OSError("Disk full")):
        with pytest.raises(OSError):
            renderer._draw_map_and_icons_with_matplotlib(
                nodes=nodes,
                edges=edges,
                bounds=None,
                icon_requests={},
                output_path=output_png,
                basemap_path="fake_basemap.png",
            )
        assert mock_bg.called


def test_static_map_renderer_create_map_early_returns(renderer_fixture, tmp_path):
    renderer, _ = renderer_fixture
    scen_dir = str(tmp_path / "scen")

    # 1. Plain xml prefix is None
    with patch("src.rendering.static_map_renderer.generate_map_data_files", return_value=None):
        img, data = renderer.create_map_with_icons("net.xml", scen_dir, {}, "out.png")
        assert img is None and data is None

    # 2. Parse map data returns None
    with patch("src.rendering.static_map_renderer.generate_map_data_files", return_value="/tmp/prefix"), \
         patch("src.rendering.static_map_renderer.parse_map_data", return_value=None):
        img, data = renderer.create_map_with_icons("net.xml", scen_dir, {}, "out.png")
        assert img is None and data is None

    # 3. Empty nodes
    with patch("src.rendering.static_map_renderer.generate_map_data_files", return_value="/tmp/prefix"), \
         patch("src.rendering.static_map_renderer.parse_map_data", return_value=({}, [], None)):
        img, data = renderer.create_map_with_icons("net.xml", scen_dir, {}, "out.png")
        assert img is None and data is None


def test_static_map_renderer_create_map_success_and_cleanup(renderer_fixture, tmp_path):
    renderer, _ = renderer_fixture
    scen_dir = str(tmp_path / "scen")
    os.makedirs(scen_dir, exist_ok=True)

    prefix = str(tmp_path / "plain_prefix")
    nod_file = prefix + ".nod.xml"
    edg_file = prefix + ".edg.xml"
    with open(nod_file, "w") as f:
        f.write("<nodes/>")
    with open(edg_file, "w") as f:
        f.write("<edges/>")

    nodes = {"n1": {"x": 0.0, "y": 0.0}}
    edges = [{"from": "n1", "to": "n1", "shape": [(0, 0), (10, 10)]}]

    with patch("src.rendering.static_map_renderer.generate_map_data_files", return_value=prefix), \
         patch("src.rendering.static_map_renderer.parse_map_data", return_value=(nodes, edges, (0, 0, 10, 10))), \
         patch.object(renderer, "_draw_map_and_icons_with_matplotlib") as mock_draw:

        img_path, map_data = renderer.create_map_with_icons("net.xml", scen_dir, {}, "test_out.png")

        assert img_path is not None
        assert map_data == (nodes, edges)
        assert mock_draw.called
        # Temporary files should be removed
        assert not os.path.exists(nod_file)
        assert not os.path.exists(edg_file)


def test_static_map_renderer_generate_coordinates_file(renderer_fixture):
    renderer, _ = renderer_fixture

    with patch("src.rendering.map_coordinate_generator.MapCoordinateGenerator.generate_coordinates_file", return_value="coords.json") as mock_gen:
        res = renderer.generate_coordinates_file(
            map_data=({}, []),
            traffic_light_ids=["tl1"],
            scenario_results_dir="/tmp/results",
        )
        assert res == "coords.json"
