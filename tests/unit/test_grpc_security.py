# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Unit and loopback tests for Synapse gRPC TLS and Bearer Token security."""

import configparser
import datetime
import ipaddress
import socket
from unittest.mock import MagicMock

import grpc
import pytest
import synapse_hft_pb2 as pb2
import synapse_hft_pb2_grpc as pb2_grpc
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from src.communication.grpc_security import BearerTokenServerInterceptor, resolve_grpc_security_config
from src.communication.grpc_server_manager import GrpcServerManager


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _write_self_signed_tls(tmp_path):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=5))
        .not_valid_after(now + datetime.timedelta(days=1))
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    cert_path = tmp_path / "server.crt"
    key_path = tmp_path / "server.key"
    cert_bytes = cert.public_bytes(serialization.Encoding.PEM)
    key_bytes = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    cert_path.write_bytes(cert_bytes)
    key_path.write_bytes(key_bytes)
    return cert_path, key_path, cert_bytes


def test_resolve_grpc_security_config_env_overrides_ini(monkeypatch):
    ini = configparser.ConfigParser()
    ini["SYNAPSE"] = {
        "grpc_auth_token": "ini-secret",
        "grpc_tls_enabled": "false",
    }
    monkeypatch.setenv("CARINA_GRPC_AUTH_TOKEN", "env-secret")
    monkeypatch.setenv("CARINA_GRPC_TLS_ENABLED", "true")
    monkeypatch.setenv("CARINA_GRPC_TLS_CERT", "/tmp/cert.pem")
    monkeypatch.setenv("CARINA_GRPC_TLS_KEY", "/tmp/key.pem")

    cfg = resolve_grpc_security_config(ini)
    assert cfg.auth_token == "env-secret"
    assert cfg.tls_enabled is True
    assert cfg.cert_path == "/tmp/cert.pem"
    assert cfg.key_path == "/tmp/key.pem"


def test_grpc_server_manager_bearer_token_and_tls_loopback(tmp_path, monkeypatch):
    cert_path, key_path, cert_bytes = _write_self_signed_tls(tmp_path)
    port = _get_free_port()

    ini = configparser.ConfigParser()
    ini["SYNAPSE"] = {
        "port": str(port),
        "max_workers": "2",
        "grpc_auth_token": "super-secret-synapse-token",
        "grpc_tls_enabled": "true",
        "grpc_tls_cert": str(cert_path),
        "grpc_tls_key": str(key_path),
    }

    monkeypatch.delenv("CARINA_GRPC_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("CARINA_GRPC_TLS_ENABLED", raising=False)

    mock_locale = MagicMock()
    mock_locale.get_string.side_effect = lambda _k, default="", **_kw: default
    mock_facade = MagicMock()

    mgr = GrpcServerManager(settings=ini, locale_manager=mock_locale, implementation_instance=mock_facade)
    mgr.start()
    try:
        creds = grpc.ssl_channel_credentials(root_certificates=cert_bytes)
        with grpc.secure_channel(f"127.0.0.1:{port}", creds) as channel:
            stub = pb2_grpc.HFTLinkStub(channel)

            # 1. Missing token -> UNAUTHENTICATED
            with pytest.raises(grpc.RpcError) as exc_unauth:
                stub.Ping(pb2.Empty(), timeout=3.0)
            assert exc_unauth.value.code() == grpc.StatusCode.UNAUTHENTICATED

            # 2. Wrong token -> UNAUTHENTICATED
            with pytest.raises(grpc.RpcError) as exc_bad:
                stub.Ping(
                    pb2.Empty(),
                    metadata=(("authorization", "Bearer wrong-token"),),
                    timeout=3.0,
                )
            assert exc_bad.value.code() == grpc.StatusCode.UNAUTHENTICATED

            # 3. Valid Bearer token over TLS -> succeeds
            resp = stub.Ping(
                pb2.Empty(),
                metadata=(("authorization", "Bearer super-secret-synapse-token"),),
                timeout=3.0,
            )
            assert resp.active is True
    finally:
        mgr.stop()


def test_bearer_interceptor_allows_when_token_empty():
    interceptor = BearerTokenServerInterceptor("")
    sentinel = object()
    assert interceptor.intercept_service(lambda _d: sentinel, MagicMock()) is sentinel
