# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

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


@pytest.mark.unit
def test_websocket_server_handler_lifecycle():
    async def _run():
        import json
        from queue import Full
        import websockets

        lm = MagicMock()
        ui_queue = MagicMock()
        server = WebSocketServer(host="127.0.0.1", port=8765, ui_command_queue=ui_queue, locale_manager=lm)

        mock_ws = AsyncMock()
        mock_ws.remote_address = ("127.0.0.1", 54321)

        # Messages: valid JSON, invalid JSON, queue full, then disconnect
        async def mock_messages():
            yield json.dumps({"cmd": "override", "tl": "TL_1"})
            yield "INVALID_JSON{{{"
            yield json.dumps({"cmd": "overflow"})

        mock_ws.__aiter__.side_effect = mock_messages

        # 3rd message causes Full queue
        ui_queue.put.side_effect = [None, Full()]

        await server._handler(mock_ws)

        assert mock_ws not in server.clients
        assert ui_queue.put.call_count == 2

    asyncio.run(_run())


@pytest.mark.unit
def test_websocket_server_broadcast_async_with_disconnected_clients():
    async def _run():
        import websockets
        lm = MagicMock()
        server = WebSocketServer(host="127.0.0.1", port=8765, locale_manager=lm)

        client1 = AsyncMock()
        client2 = AsyncMock()
        client2.send.side_effect = ConnectionResetError("Disconnected")

        server.clients.add(client1)
        server.clients.add(client2)

        await server._broadcast_async('{"data": 123}')

        client1.send.assert_called_once_with('{"data": 123}')
        # client2 should have been unregistered
        assert client2 not in server.clients
        assert client1 in server.clients

        # Empty clients branch
        server.clients.clear()
        await server._broadcast_async('{"data": 123}')

    asyncio.run(_run())


@pytest.mark.unit
def test_websocket_server_main_loop_port_fallback_and_fatal():
    async def _run():
        import websockets
        lm = MagicMock()
        server = WebSocketServer(host="127.0.0.1", port=8765, locale_manager=lm)

        # 1. Port 8765 busy (errno 98), port 8766 succeeds
        err_busy = OSError()
        err_busy.errno = 98

        mock_srv = AsyncMock()
        mock_srv.__aenter__.return_value = mock_srv
        mock_srv.__aexit__.return_value = None

        calls = [err_busy, mock_srv]
        async def fake_serve(*args, **kwargs):
            res = calls.pop(0)
            if isinstance(res, Exception):
                raise res
            return res

        with patch("websockets.serve", side_effect=fake_serve), \
             patch("asyncio.Future", side_effect=asyncio.CancelledError):
            try:
                await server._main_loop()
            except asyncio.CancelledError:
                pass
            assert server.port == 8766

        # 2. All 3 ports busy -> fatal error logged
        server.port = 8765
        async def fake_serve_all_fail(*args, **kwargs):
            raise err_busy

        with patch("websockets.serve", side_effect=fake_serve_all_fail):
            await server._main_loop()

    asyncio.run(_run())



@pytest.mark.unit
def test_websocket_server_start_and_stop():
    lm = MagicMock()
    server = WebSocketServer(host="127.0.0.1", port=8765, locale_manager=lm)

    with patch.object(server, "_main_loop", return_value=None):
        server.start()
        assert server.thread is not None
        assert server.loop is not None
        server.stop()

