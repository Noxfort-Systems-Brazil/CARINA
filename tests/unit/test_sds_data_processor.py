# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import configparser
from unittest.mock import MagicMock, patch
import pytest

from src.sds.data_processor import DataProcessor


@pytest.fixture
def processor_fixture():
    settings = configparser.ConfigParser()
    settings.add_section("HEATMAP_UPDATES")
    settings.set("HEATMAP_UPDATES", "update_interval_seconds", "2.5")

    lm = MagicMock()
    lm.get_string.side_effect = lambda k, **kw: f"mock_{k}"

    proc = DataProcessor(settings=settings, locale_manager=lm)
    return proc, lm


def test_data_processor_init(processor_fixture):
    proc, _ = processor_fixture
    assert proc.heatmap_update_interval == 2.5
    assert proc.geometry_sent is False


def test_data_processor_tuple_messages(processor_fixture):
    proc, _ = processor_fixture

    with patch("src.sds.tls_state_formatter.TlsStateFormatter.load_network_topology") as mock_load_topo:
        # 1. initial_map_geometry
        res = proc.process_for_ui(("initial_map_geometry", {"net_file": "test.net.xml"}))
        assert res["type"] == "initial_map_geometry"
        assert proc.geometry_sent is True
        mock_load_topo.assert_called_once_with("test.net.xml")

    # 2. update_heatmap
    res_hm = proc.process_for_ui(("update_heatmap", {"edges": {"e1": 12.0}}))
    assert res_hm["type"] == "congestion_update"
    assert res_hm["payload"] == {"e1": 12.0}

    # 3. hft_rich_update with edges
    payload_rich = {
        "edges": {"e1": {"congestion": 45.0}},
        "maturity": {"tl_1": "ADULT"},
    }
    with patch("src.sds.tls_state_formatter.TlsStateFormatter.prepare_panel_data", return_value={"panel": 1}):
        res_rich = proc.process_for_ui(("hft_rich_update", payload_rich))
        assert res_rich["type"] == "congestion_update"
        assert res_rich["payload"]["e1"] == 45.0
        assert res_rich["maturity_phases"]["tl_1"] == "ADULT"

    # 4. hft_rich_update without edges (fast_update)
    with patch("src.sds.tls_state_formatter.TlsStateFormatter.prepare_panel_data", return_value={"panel": 1}):
        res_fast = proc.process_for_ui(("hft_rich_update", {"maturity": {}}))
        assert res_fast["type"] == "fast_update"

    # 5. Security & Account messages
    for msg_type in ["auth_response", "lockdown_event", "account_response", "users_list", "audit_logs_response"]:
        res_sec = proc.process_for_ui((msg_type, {"data": 1}))
        assert res_sec["type"] == msg_type

    # 6. Unknown tuple
    assert proc.process_for_ui(("unknown_type", {})) is None


def test_data_processor_legacy_dict(processor_fixture):
    proc, _ = processor_fixture
    proc.map_data = ({"n1": (0, 0)}, [{"id": "e1"}], None)
    proc.lane_to_edge_map = {"lane_1": "e1"}
    proc.geometry_sent = False

    raw_data = {
        "maturity_phases": {"tl_1": "ADULT"},
        "edge_metrics": {},
    }

    with patch.object(proc.metrics_calculator, "calculate_street_data", return_value={"e1": {"congestion": 25.0}}), \
         patch("src.sds.tls_state_formatter.TlsStateFormatter.prepare_panel_data", return_value={"p": 1}):

        # First legacy call -> initial_map_geometry
        res1 = proc.process_for_ui(raw_data)
        assert res1["type"] == "initial_map_geometry"
        assert res1["congestion_update"] == {"e1": 25.0}
        assert proc.geometry_sent is True

        # Second legacy call -> congestion_update
        res2 = proc.process_for_ui(raw_data)
        assert res2["type"] == "congestion_update"
        assert res2["payload"] == {"e1": 25.0}


def test_data_processor_lazy_load_map_data(processor_fixture, tmp_path):
    proc, _ = processor_fixture

    with patch("src.sds.tls_state_formatter.TlsStateFormatter.load_network_topology") as mock_topo, \
         patch("src.utils.paths.get_base_output_dir", return_value=str(tmp_path)), \
         patch("src.sds.data_processor.parse_map_data", return_value=({"n1": 1}, [], None)), \
         patch("src.sds.data_processor.build_lane_to_edge_map", return_value={"l1": "e1"}):


        # Fake net file
        net_file = tmp_path / "fake.net.xml"
        net_file.write_text("<net/>")

        # Fake nod.xml to simulate pre-existing map files
        maps_dir = tmp_path / "results" / "scen1" / "maps"
        maps_dir.mkdir(parents=True, exist_ok=True)
        (maps_dir / "scen1_map.nod.xml").write_text("<nodes/>")

        proc._lazy_load_map_data(str(net_file), "scen1")

        assert proc.map_data is not None
        assert proc.lane_to_edge_map == {"l1": "e1"}
        assert proc.edge_to_lanes_map["e1"] == ["l1"]
        mock_topo.assert_called_once_with(str(net_file))
