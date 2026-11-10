# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import os
from unittest.mock import MagicMock, patch
import pytest

from src.controller.topology_manager import ControllerTopologyCoordinator, TopologyManager


@pytest.fixture
def topo_fixture():
    ai_pipe = MagicMock()
    sds_queue = MagicMock()
    mgr = ControllerTopologyCoordinator("/fake/root", ai_pipe, sds_queue)
    return mgr, ai_pipe, sds_queue


def test_topology_manager_init(topo_fixture):
    mgr, ai_pipe, sds_queue = topo_fixture
    assert mgr.project_root == "/fake/root"
    assert mgr.ai_pipe_conn is ai_pipe
    assert mgr.sds_data_queue is sds_queue
    assert mgr.agent_maturity_cache == {}
    assert mgr.net_file_path is None
    # Alias check
    assert TopologyManager is ControllerTopologyCoordinator


def test_try_restore_state_with_json_and_net_xml(topo_fixture, tmp_path):
    mgr, ai_pipe, sds_queue = topo_fixture

    maps_dir = tmp_path / "results" / "hft_live_session" / "maps"
    maps_dir.mkdir(parents=True, exist_ok=True)

    json_file = maps_dir / "map_topology.json"
    json_file.write_text(
        json.dumps({"nodes": [{"id": "tl_1", "type": "traffic_light"}, {"id": "n2", "type": "priority"}]}),
        encoding="utf-8",
    )

    net_file = maps_dir / "city.net.xml"
    net_file.write_text("<net/>", encoding="utf-8")

    with patch("src.utils.paths.get_base_output_dir", return_value=str(tmp_path)), \
         patch("time.sleep", return_value=None):

        mgr.try_restore_state()

        assert mgr.agent_maturity_cache.get("tl_1") == "CHILD"
        assert "n2" not in mgr.agent_maturity_cache
        assert mgr.net_file_path == str(net_file)
        ai_pipe.send.assert_called_once_with(("custom", "load_map", (str(net_file),), {}))
        sds_queue.put.assert_called_once_with(("initial_map_geometry", {"net_file": str(net_file)}))


def test_try_restore_state_missing_json_extracts(topo_fixture, tmp_path):
    mgr, ai_pipe, sds_queue = topo_fixture

    maps_dir = tmp_path / "results" / "hft_live_session" / "maps"
    maps_dir.mkdir(parents=True, exist_ok=True)

    net_file = maps_dir / "city.net.xml.gz"
    net_file.write_text("mock gz", encoding="utf-8")

    with patch("src.utils.paths.get_base_output_dir", return_value=str(tmp_path)), \
         patch("src.utils.map_processor.MapProcessor.extract_topology_to_json", return_value={"tl_2": "CHILD"}) as mock_extract, \
         patch("time.sleep", return_value=None):

        mgr.try_restore_state()

        assert mock_extract.called
        assert mgr.agent_maturity_cache.get("tl_2") == "CHILD"
        assert mgr.net_file_path == str(net_file)


def test_try_restore_state_no_net_xml(topo_fixture, tmp_path):
    mgr, ai_pipe, sds_queue = topo_fixture

    maps_dir = tmp_path / "results" / "hft_live_session" / "maps"
    maps_dir.mkdir(parents=True, exist_ok=True)

    with patch("src.utils.paths.get_base_output_dir", return_value=str(tmp_path)):
        mgr.try_restore_state()
        assert not ai_pipe.send.called
        assert not sds_queue.put.called


def test_handle_new_map_success_and_resets(topo_fixture, tmp_path):
    mgr, ai_pipe, sds_queue = topo_fixture
    maps_dir = str(tmp_path / "maps")
    map_file = str(tmp_path / "new_map.net.xml")

    mock_agg = MagicMock()

    with patch("src.utils.map_processor.MapProcessor.extract_topology_to_json", return_value={"tl_new": "CHILD"}):
        mgr.handle_new_map(map_file, maps_dir, mock_agg)

        assert mgr.agent_maturity_cache.get("tl_new") == "CHILD"
        assert mock_agg.reset.called
        assert mgr.net_file_path == map_file
        ai_pipe.send.assert_called_once_with(("custom", "load_map", (map_file,), {}))
        sds_queue.put.assert_called_once_with(("initial_map_geometry", {"net_file": map_file}))


def test_handle_new_map_exceptions_handled(topo_fixture, tmp_path):
    mgr, ai_pipe, sds_queue = topo_fixture

    ai_pipe.send.side_effect = RuntimeError("AI pipe broke")
    sds_queue.put.side_effect = RuntimeError("SDS queue broke")

    with patch("src.utils.map_processor.MapProcessor.extract_topology_to_json", side_effect=RuntimeError("Parse fail")):
        # Should not raise exception
        mgr.handle_new_map("bad_map.xml", str(tmp_path), None)
