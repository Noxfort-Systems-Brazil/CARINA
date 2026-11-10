# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from unittest.mock import MagicMock, patch
import pytest

from src.rendering.heatmap_renderer import HeatmapRenderer


@pytest.fixture
def renderer_fixture():
    lm = MagicMock()
    lm.get_string.side_effect = lambda k, **kw: f"mock_{k}"
    renderer = HeatmapRenderer(locale_manager=lm)
    return renderer


def test_heatmap_renderer_precise_color(renderer_fixture):
    renderer = renderer_fixture

    # 0.0 -> dark green
    c0 = renderer.get_precise_color_for_congestion(0.0)
    assert len(c0) == 3
    assert c0[1] > c0[0]  # green > red

    # 50.0 -> yellow
    c50 = renderer.get_precise_color_for_congestion(50.0)
    assert c50[0] > 0.5 and c50[1] > 0.5

    # 100.0 -> red
    c100 = renderer.get_precise_color_for_congestion(100.0)
    assert c100[0] == 1.0 and c100[1] == 0.0

    # Over 100.0 -> clamped to 1.0
    c150 = renderer.get_precise_color_for_congestion(150.0)
    assert c150 == c100


def test_heatmap_renderer_enhanced_color(renderer_fixture):
    renderer = renderer_fixture

    # Zero
    c0 = renderer.get_enhanced_color_for_congestion(0.0)
    assert len(c0) == 3

    # Low range (< 0.3)
    c10 = renderer.get_enhanced_color_for_congestion(10.0)
    assert len(c10) == 3

    # Mid range (0.3 - 0.7)
    c50 = renderer.get_enhanced_color_for_congestion(50.0)
    assert len(c50) == 3

    # High range (> 0.7)
    c85 = renderer.get_enhanced_color_for_congestion(85.0)
    assert len(c85) == 3

    # Max
    c100 = renderer.get_enhanced_color_for_congestion(100.0)
    assert c100[0] == 1.0 and c100[1] == 0.0


def test_heatmap_renderer_create_heatmap_and_cache(renderer_fixture):
    renderer = renderer_fixture

    nodes = {
        "n1": {"x": 10.0, "y": 20.0},
        "n2": {"x": 30.0, "y": 40.0},
    }
    edges = [
        {"id": "edge_1", "shape": [(10.0, 20.0), (30.0, 40.0)]},
        {"id": "edge_short", "shape": [(10.0, 20.0)]},  # len < 2
        {"id": "edge_no_data", "shape": [(0.0, 0.0), (1.0, 1.0)]},
    ]
    map_data = (nodes, edges)
    congestion_data = {"edge_1": 45.0, "edge_short": 10.0}

    # 1. First render (in-memory)
    img_b64 = renderer.create_heatmap_image_in_memory(map_data, congestion_data, saturation_threshold=100.0)
    assert img_b64 is not None
    assert len(img_b64) > 50

    # 2. Second render (cache hit)
    img_b64_cached = renderer.create_heatmap_image_in_memory(map_data, congestion_data, saturation_threshold=100.0)
    assert img_b64_cached == img_b64

    # 3. Cache eviction test: fill cache beyond limit of 5
    for i in range(6):
        renderer.create_heatmap_image_in_memory(map_data, {"edge_1": float(i * 10)}, saturation_threshold=100.0)
    assert len(renderer._cache) <= 5

    # 4. Clear cache
    renderer.clear_cache()
    assert len(renderer._cache) == 0


def test_heatmap_renderer_create_heatmap_error_handling(renderer_fixture):
    renderer = renderer_fixture

    with patch("matplotlib.pyplot.subplots", side_effect=RuntimeError("Plot crash")):
        res = renderer.create_heatmap_image_in_memory(({}, []), {"edge_1": 10.0})
        assert res is None
