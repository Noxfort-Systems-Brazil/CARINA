# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
gRPC Transport Security (TLS/mTLS credentials and Bearer Token interceptor) for Synapse HFT Link.
Designed to preserve backward-compatible plaintext/unauthenticated behavior when security settings are unset.
"""

import hmac
import logging
import os
from dataclasses import dataclass
from typing import Any, Optional, Sequence, Tuple

import grpc

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GrpcSecurityConfig:
    """Resolved gRPC server security parameters."""

    auth_token: str = ""
    tls_enabled: bool = False
    cert_path: str = ""
    key_path: str = ""
    ca_path: str = ""
    require_client_cert: bool = False


def _read_setting_str(settings: Any, section: str, key: str, fallback: str = "") -> str:
    if settings is None or not hasattr(settings, "get"):
        return fallback
    try:
        val = settings.get(section, key, fallback=fallback)
        return val.strip() if isinstance(val, str) else fallback
    except Exception:
        return fallback


def _parse_bool(raw: Any, fallback: bool = False) -> bool:
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        val = raw.strip().lower()
        if val in {"1", "true", "yes", "on"}:
            return True
        if val in {"0", "false", "no", "off"}:
            return False
    return fallback


def resolve_grpc_security_config(settings: Any = None) -> GrpcSecurityConfig:
    """Resolves gRPC security parameters prioritizing environment variables over INI settings."""
    ini_token = _read_setting_str(settings, "SYNAPSE", "grpc_auth_token", "")
    auth_token = os.getenv("CARINA_GRPC_AUTH_TOKEN", ini_token).strip()

    ini_tls = _read_setting_str(settings, "SYNAPSE", "grpc_tls_enabled", "false")
    tls_raw = os.getenv("CARINA_GRPC_TLS_ENABLED", ini_tls)
    tls_enabled = _parse_bool(tls_raw, fallback=False)

    cert_path = os.getenv("CARINA_GRPC_TLS_CERT", _read_setting_str(settings, "SYNAPSE", "grpc_tls_cert", "")).strip()
    key_path = os.getenv("CARINA_GRPC_TLS_KEY", _read_setting_str(settings, "SYNAPSE", "grpc_tls_key", "")).strip()
    ca_path = os.getenv("CARINA_GRPC_TLS_CA", _read_setting_str(settings, "SYNAPSE", "grpc_tls_ca", "")).strip()
    req_client_raw = os.getenv(
        "CARINA_GRPC_REQUIRE_CLIENT_CERT",
        _read_setting_str(settings, "SYNAPSE", "grpc_require_client_cert", "false"),
    )
    require_client_cert = _parse_bool(req_client_raw, fallback=False)

    return GrpcSecurityConfig(
        auth_token=auth_token,
        tls_enabled=tls_enabled,
        cert_path=cert_path,
        key_path=key_path,
        ca_path=ca_path,
        require_client_cert=require_client_cert,
    )


def build_grpc_server_credentials(cfg: GrpcSecurityConfig) -> Optional[grpc.ServerCredentials]:
    """Builds SSL/TLS (and optional mTLS) server credentials when configured."""
    if not cfg.tls_enabled:
        return None
    if not cfg.cert_path or not cfg.key_path:
        raise ValueError("CARINA gRPC TLS enabled, but certificate or private key path is missing.")

    with open(cfg.key_path, "rb") as kf:
        private_key = kf.read()
    with open(cfg.cert_path, "rb") as cf:
        certificate_chain = cf.read()

    root_certs = None
    if cfg.ca_path:
        with open(cfg.ca_path, "rb") as caf:
            root_certs = caf.read()

    return grpc.ssl_server_credentials(
        [(private_key, certificate_chain)],
        root_certificates=root_certs,
        require_client_auth=bool(cfg.require_client_cert and root_certs is not None),
    )


def _extract_metadata_token(metadata: Optional[Sequence[Tuple[str, str]]]) -> str:
    if not metadata:
        return ""
    for key, value in metadata:
        k_lower = str(key).lower()
        val = str(value).strip()
        if k_lower == "authorization" and val.lower().startswith("bearer "):
            return val[7:].strip()
        if k_lower == "x-carina-token" and val:
            return val
    return ""


def _deny_handler(next_handler: grpc.RpcMethodHandler) -> grpc.RpcMethodHandler:
    def _abort(_request, context):
        context.abort(grpc.StatusCode.UNAUTHENTICATED, "Unauthorized gRPC request: valid bearer token required.")

    req_stream = bool(getattr(next_handler, "request_streaming", False))
    resp_stream = bool(getattr(next_handler, "response_streaming", False))

    if req_stream and resp_stream:
        return grpc.stream_stream_rpc_method_handler(_abort)
    if req_stream:
        return grpc.stream_unary_rpc_method_handler(_abort)
    if resp_stream:
        return grpc.unary_stream_rpc_method_handler(_abort)
    return grpc.unary_unary_rpc_method_handler(_abort)


class BearerTokenServerInterceptor(grpc.ServerInterceptor):
    """Enforces constant-time Bearer / X-Carina-Token verification on incoming gRPC RPCs."""

    def __init__(self, expected_token: str) -> None:
        self._expected_token = expected_token.strip()

    def intercept_service(self, continuation, handler_call_details):
        next_handler = continuation(handler_call_details)
        if next_handler is None or not self._expected_token:
            return next_handler

        token = _extract_metadata_token(getattr(handler_call_details, "invocation_metadata", None))
        if not token or not hmac.compare_digest(token, self._expected_token):
            logger.warning("[GrpcSecurity] Rejected unauthenticated gRPC call to %s", handler_call_details.method)
            return _deny_handler(next_handler)
        return next_handler
