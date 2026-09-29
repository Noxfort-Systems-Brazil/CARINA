# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Noxfort Systems
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
# along with this program. If not, see <https://www.gnu.org/licenses/>.

# File: tests/unit/test_sds_streaming.py
# Author: Gabriel Moraes
# Date: September 2026

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sds.edge_data_processor import EdgeDataProcessor
from sds.periodic_data_collector import PeriodicDataCollector
from sds.websocket_server import WebSocketServer


@pytest.mark.unit
def test_edge_data_processor_normalization():
    proc = EdgeDataProcessor()
    assert proc._normalize_edge_id("edge_1") == "edge_1"
    assert proc._normalize_edge_id("-edge_1") == "edge_1"
    assert proc._normalize_edge_id("edge_1#0") == "edge_1"
    assert proc._normalize_edge_id("-edge_1#2") == "edge_1"


@pytest.mark.unit
def test_edge_data_processor_grouping():
    proc = EdgeDataProcessor()
    buffer_data = {
        "edge_A#0": {"occ": [0.2], "spd": [12.0], "q": [2]},
        "-edge_A#1": {"occ": [0.3], "spd": [10.0], "q": [3]},
        "edge_B": {"occ": [0.1], "spd": [14.0], "q": [0]},
    }
    grouped = proc.group_edge_data(buffer_data)
    assert "edge_A" in grouped
    assert "edge_B" in grouped
    assert grouped["edge_A"]["occ"] == [0.2, 0.3]
    assert len(grouped["edge_A"]["original_edges"]) == 2


@pytest.mark.unit
def test_edge_data_processor_metrics():
    proc = EdgeDataProcessor()

    # Empty case
    empty_res = proc.compute_congestion_metrics({"occ": [], "spd": [], "q": []})
    assert empty_res["congestion"] == 0.0
    assert empty_res["vehicles"] == 0

    # Low congestion (free flow)
    free_flow = proc.compute_congestion_metrics({"occ": [0.05, 0.05], "spd": [16.67, 16.67], "q": [0, 0]})
    assert free_flow["congestion"] < 10.0
    assert free_flow["speed"] > 50.0

    # High congestion (low speed, long queue)
    congested = proc.compute_congestion_metrics({"occ": [0.8, 0.9], "spd": [2.0, 1.5], "q": [25, 30]})
    assert congested["congestion"] > 70.0
    assert congested["vehicles"] >= 25


@pytest.mark.unit
def test_periodic_data_collector():
    collector = PeriodicDataCollector(update_interval=2.0)
    assert not collector.should_update(100.0)

    # Add sample
    collector.add_sample(100.0, {"edge_1": {"occupancy": 0.2, "speed": 12.0, "queue": 2}})

    # Not enough time passed
    assert collector.compute_aggregated_payload(101.0, {"agent_1": "ADULT"}) is None

    # Enough time passed
    payload = collector.compute_aggregated_payload(103.0, {"agent_1": "ADULT"})
    assert payload is not None
    assert payload["timestamp"] == 103.0
    assert "edge_1" in payload["edges"]
    assert payload["maturity"]["agent_1"] == "ADULT"

    stats = collector.get_stats()
    assert "samples_collected" in stats

    collector.reset()
    assert collector.get_stats()["samples_collected"] == 0


@pytest.mark.unit
def test_websocket_server_initialization_and_cache():
    lm = MagicMock()
    server = WebSocketServer(host="127.0.0.1", port=8765, locale_manager=lm)
    server.loop = MagicMock()
    assert server.port == 8765
    assert len(server.clients) == 0

    # Initial map geometry caching
    msg = {"type": "initial_map_geometry", "data": [1, 2, 3]}
    server.broadcast(msg)
    assert server.cached_initial_geometry_packet is not None
    assert "initial_map_geometry" in server.cached_initial_geometry_packet


@pytest.mark.unit
def test_websocket_server_registration():
    async def _run():
        lm = MagicMock()
        server = WebSocketServer(host="127.0.0.1", port=8765, locale_manager=lm)
        server.cached_initial_geometry_packet = '{"type": "cached"}'

        mock_ws = AsyncMock()
        mock_ws.remote_address = ("127.0.0.1", 54321)

        # Register client
        await server._register(mock_ws)
        assert mock_ws in server.clients
        mock_ws.send.assert_called_once_with('{"type": "cached"}')

        # Unregister client
        await server._unregister(mock_ws)
        assert mock_ws not in server.clients

    asyncio.run(_run())
