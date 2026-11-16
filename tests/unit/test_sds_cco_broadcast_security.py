# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import datetime
import ipaddress
import json
import ssl
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import MagicMock, patch

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from src.sds.cco_broadcast_client import CCOBroadcastClient
from src.sds.sds_process_starter import SDSProcessStarter


def _write_self_signed_cert(cert_path: Path, key_path: Path, include_loopback_san: bool = True) -> None:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "carina-cco-test")])
    now = datetime.datetime.now(datetime.timezone.utc)
    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=5))
        .not_valid_after(now + datetime.timedelta(hours=1))
    )
    if include_loopback_san:
        builder = builder.add_extension(
            x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]),
            critical=False,
        )
    cert = builder.sign(key, hashes.SHA256())
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
    )
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))


def _start_cco_mock_server(token_box: dict, tls_pair=None):
    received = []

    class _Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            return

        def do_GET(self):
            if self.path == "/":
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"OK")
                return
            self.send_response(404)
            self.end_headers()

        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(length)
            auth = self.headers.get("Authorization", "")
            expected = f"Bearer {token_box['token']}" if token_box.get("token") else ""
            if expected and auth != expected:
                self.send_response(401)
                self.end_headers()
                self.wfile.write(b'{"error":"unauthorized"}')
                return
            received.append(json.loads(raw_body.decode("utf-8")))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"broadcasted"}')

    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    if tls_pair is not None:
        cert_file, key_file = tls_pair
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(certfile=str(cert_file), keyfile=str(key_file))
        srv.socket = ctx.wrap_socket(srv.socket, server_side=True)

    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    return srv, srv.server_address[1], received


def test_cco_broadcast_bearer_auth_and_401_token_rotation(monkeypatch):
    token_state = {"token": "cco-secret-1"}
    srv, port, received = _start_cco_mock_server(token_state)
    try:
        monkeypatch.setenv("CARINA_GATEWAY_PORT", str(port))
        monkeypatch.delenv("CARINA_GATEWAY_TLS_CERT", raising=False)
        monkeypatch.delenv("CARINA_GATEWAY_TLS_KEY", raising=False)
        monkeypatch.delenv("CARINA_GATEWAY_TLS_CA", raising=False)

        client = CCOBroadcastClient(timeout=1.0, config_ttl_sec=60.0)
        with patch.object(CCOBroadcastClient, "_load_settings_dict", return_value={}):
            # Missing token triggers HTTP 401 and returns False
            monkeypatch.setenv("CARINA_CCO_AUTH_TOKEN", "wrong-token")
            assert client.broadcast({"step": 1}) is False
            assert len(received) == 0

            # Valid Bearer token delivers payload
            monkeypatch.setenv("CARINA_CCO_AUTH_TOKEN", "cco-secret-1")
            client.reset()
            assert client.broadcast({"step": 2}) is True
            assert len(received) == 1
            assert received[0]["type"] == "congestion_update"
            assert received[0]["step"] == 2

            # Server rotates token; client encounters HTTP 401 and forces refresh retry
            token_state["token"] = "cco-secret-2"
            monkeypatch.setenv("CARINA_CCO_AUTH_TOKEN", "cco-secret-2")
            assert client.broadcast({"step": 3}) is True
            assert len(received) == 2
            assert received[1]["step"] == 3
    finally:
        srv.shutdown()
        srv.server_close()


def test_cco_broadcast_https_with_leaf_cert_pinning_and_mismatch_rejection(tmp_path: Path, monkeypatch):
    cert_path = tmp_path / "gw.crt"
    key_path = tmp_path / "gw.key"
    wrong_cert = tmp_path / "wrong.crt"
    wrong_key = tmp_path / "wrong.key"
    # Deliberately omit loopback IP SAN to validate SHA-256 cert pinning path used on self-signed local certs
    _write_self_signed_cert(cert_path, key_path, include_loopback_san=False)
    _write_self_signed_cert(wrong_cert, wrong_key, include_loopback_san=False)

    srv, port, received = _start_cco_mock_server({"token": "tls-token"}, tls_pair=(cert_path, key_path))
    try:
        monkeypatch.setenv("CARINA_GATEWAY_PORT", str(port))
        monkeypatch.setenv("CARINA_CCO_AUTH_TOKEN", "tls-token")
        monkeypatch.setenv("CARINA_GATEWAY_TLS_CERT", str(cert_path))
        monkeypatch.setenv("CARINA_GATEWAY_TLS_KEY", str(key_path))
        monkeypatch.delenv("CARINA_GATEWAY_TLS_CA", raising=False)
        monkeypatch.delenv("CARINA_GATEWAY_TLS_SERVER_NAME", raising=False)

        client = CCOBroadcastClient(timeout=1.5, config_ttl_sec=60.0)
        with patch.object(CCOBroadcastClient, "_load_settings_dict", return_value={}):
            assert client.broadcast({"tls": "ok"}) is True
            assert len(received) == 1
            assert received[0]["tls"] == "ok"

            # SDSProcessStarter.is_port_active should validate HTTPS endpoint too
            starter = SDSProcessStarter()
            assert starter.is_port_active(port=port, timeout=1.0) is True

            # Mismatched client cert/pin must be rejected (prevents MITM)
            monkeypatch.setenv("CARINA_GATEWAY_TLS_CERT", str(wrong_cert))
            monkeypatch.setenv("CARINA_GATEWAY_TLS_KEY", str(wrong_key))
            client.reset()
            assert client.broadcast({"tls": "should-fail"}) is False
            assert len(received) == 1
    finally:
        srv.shutdown()
        srv.server_close()


def test_ui_network_event_handler_delegates_broadcast_to_authenticated_client(monkeypatch):
    from ui.handlers.network_event_handler import NetworkEventHandler

    srv, port, received = _start_cco_mock_server({"token": "ui-token"})
    try:
        monkeypatch.setenv("CARINA_GATEWAY_PORT", str(port))
        monkeypatch.setenv("CARINA_CCO_AUTH_TOKEN", "ui-token")
        monkeypatch.delenv("CARINA_GATEWAY_TLS_CERT", raising=False)
        monkeypatch.delenv("CARINA_GATEWAY_TLS_KEY", raising=False)

        handler = NetworkEventHandler(
            page=MagicMock(),
            dashboard_view=MagicMock(),
            security_ui=MagicMock(),
            settings_view=MagicMock(),
            locale_manager=MagicMock(),
        )
        with patch.object(CCOBroadcastClient, "_load_settings_dict", return_value={}):
            handler._broadcast_to_cco({"source": "ui_fallback", "speed": 42})
        assert len(received) == 1
        assert received[0]["source"] == "ui_fallback"
        assert received[0]["speed"] == 42
    finally:
        srv.shutdown()
        srv.server_close()
