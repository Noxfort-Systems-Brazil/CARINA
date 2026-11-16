# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import sqlite3
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import MappingProxyType
from unittest.mock import MagicMock

from src.evp.evp_db_executor import AsyncTelemetryPersistQueue
from src.evp.evp_kinematics import EVPKinematicsEngine
from src.evp.evp_models import CorporationType, EmergencyVehicle, RegisteredVehicle, TelemetryData
from src.evp.evp_notifier import EVPNotifier
from src.evp.evp_service import EVPService
from src.evp.evp_telemetry_repository import EVPTelemetryRepository
from src.evp.evp_topology_service import EVPTopologyService
from src.sds.cco_broadcast_client import CCOBroadcastClient
from ui.animators.map_animator import MapAnimator
from ui.cards.evp_fleet_connection_card import EVPFleetConnectionCard
from ui.handlers.locale_manager import LocaleManager
from ui.managers.window_manager import WindowManager
from ui.widgets.audit_log_widget import AuditLogWidget


def test_cco_broadcast_reuses_http11_keepalive_connection_and_async_queue(monkeypatch):
    reqs = []

    class _KeepAliveHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, format, *args):
            return

        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            reqs.append((self.client_address, json.loads(self.rfile.read(length).decode("utf-8"))))
            resp = b'{"ok":true}'
            self.send_response(200)
            self.send_header("Content-Length", str(len(resp)))
            self.end_headers()
            self.wfile.write(resp)

    srv = ThreadingHTTPServer(("127.0.0.1", 0), _KeepAliveHandler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    client = None
    try:
        monkeypatch.setenv("CARINA_GATEWAY_PORT", str(srv.server_address[1]))
        monkeypatch.delenv("CARINA_GATEWAY_TLS_CERT", raising=False)
        monkeypatch.delenv("CARINA_CCO_AUTH_TOKEN", raising=False)
        client = CCOBroadcastClient(timeout=1.0, config_ttl_sec=60.0)
        assert client.broadcast({"step": 1}) is True
        assert client.broadcast({"step": 2}) is True
        # Same ephemeral client port proves TCP keep-alive socket reuse
        assert reqs[0][0] == reqs[1][0]

        client.enqueue_broadcast({"step": 3})
        deadline = time.monotonic() + 2.0
        while len(reqs) < 3 and time.monotonic() < deadline:
            time.sleep(0.02)
        assert len(reqs) == 3
    finally:
        if client is not None:
            client.close()
        srv.shutdown()
        srv.server_close()


def test_evp_readonly_snapshot_lock_release_before_rpc_and_batch_persist():
    topo = EVPTopologyService()
    topo.register_intersection("INT_1", -23.55, -46.63, target_stage=1)
    ro = topo.get_intersections_readonly()
    assert isinstance(ro, MappingProxyType)
    assert topo.get_intersections_readonly() is ro

    in_rpc = threading.Event()
    release_rpc = threading.Event()
    snapshot_elapsed = []

    def slow_dispatch(int_id, stage, action):
        in_rpc.set()
        release_rpc.wait(timeout=1.0)

    persisted_batches = []
    q = AsyncTelemetryPersistQueue(lambda batch: persisted_batches.append(list(batch)), max_batch=8)

    service = EVPService(
        topology_service=topo,
        kinematics=EVPKinematicsEngine(block_entry_min_meters=60.0, block_entry_max_meters=200.0),
        on_action_dispatch=slow_dispatch,
    )
    service.register_fleet_vehicle(RegisteredVehicle(vehicle_id="AMB_1", corporation=CorporationType.SAMU))

    int_lat, _ = ro["INT_1"]
    t_data = TelemetryData(
        vehicle_id="AMB_1",
        corporation=CorporationType.SAMU,
        latitude=int_lat + (100.0 / 111139.0),
        longitude=-46.63,
        speed_kmh=50.0,
        heading_deg=0.0,
        siren_active=True,
    )

    worker = threading.Thread(target=lambda: service.process_telemetry(t_data), daemon=True)
    worker.start()
    assert in_rpc.wait(timeout=1.0)
    t0 = time.perf_counter()
    snap = service.export_remote_snapshot()
    snapshot_elapsed.append(time.perf_counter() - t0)
    release_rpc.set()
    worker.join(timeout=1.0)

    assert snap is not None
    assert snapshot_elapsed[0] < 0.25

    conn = sqlite3.connect(":memory:")
    engine = MagicMock()
    engine.db_type = "sqlite"
    engine.get_connection.return_value = conn
    repo = EVPTelemetryRepository(engine, close_conn_fn=lambda c: None)
    veh = EmergencyVehicle(
        vehicle_id="AMB_1", corporation=CorporationType.SAMU, latitude=-23.55, longitude=-46.63, siren_active=True
    )
    snap_row = EVPTelemetryRepository.snapshot_telemetry(veh, True)
    q.enqueue(snap_row)
    q.stop()
    assert len(persisted_batches) == 1
    assert repo.save_telemetry_batch(persisted_batches[0]) == 1
    conn.close()


def test_ui_evp_card_unregisters_listener_and_window_hidden_and_audit_pagination(tmp_path):
    notifier = EVPNotifier.get_instance()
    before_count = len(notifier._listeners)
    card = EVPFleetConnectionCard(locale_manager=MagicMock())
    assert len(notifier._listeners) == before_count + 1
    card.will_unmount()
    assert len(notifier._listeners) == before_count

    mock_page = MagicMock()
    mock_page.window = MagicMock()
    wm = WindowManager(mock_page, threading.Event(), threading.Event())
    ev = MagicMock()
    ev.data = "close"
    wm._window_event(ev)
    assert getattr(mock_page, "_carina_window_hidden", False) is True

    mock_widget = MagicMock()
    mock_widget.page = mock_page
    anim = MapAnimator(widget_to_update=mock_widget)
    assert anim._is_window_hidden() is True

    audit_path = tmp_path / "audit_logs.json"
    entries = [
        {"timestamp": "2026-01-01T12:00:00", "username": "op", "action": f"ACT_{i}", "details": "ok"}
        for i in range(150)
    ]
    audit_path.write_text(json.dumps(entries), encoding="utf-8")
    lm = MagicMock(spec=LocaleManager)
    lm.get_string.side_effect = lambda k, default=None, **kw: default or k
    widget = AuditLogWidget(locale_manager=lm)
    widget.audit_file = str(audit_path)
    widget._load_logs()
    assert len(widget.table.rows) == 100
    assert widget.next_btn.visible is True
    widget._next_page()
    assert len(widget.table.rows) == 50
