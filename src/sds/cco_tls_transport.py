# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""TLS config, certificate SHA-256 pinning, and HTTP/HTTPS connection factory for CCOBroadcastClient."""

import hashlib
import hmac
import http.client
import logging
import os
import re
import ssl
from dataclasses import dataclass
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BroadcastConfig:
    scheme: str = "http"
    port: int = 2201
    cco_auth_token: str = ""
    tls_cert: str = ""
    tls_key: str = ""
    tls_ca: str = ""
    tls_server_name: str = ""

    @property
    def broadcast_url(self) -> str:
        return f"{self.scheme}://127.0.0.1:{self.port}/cco/broadcast"

    @property
    def health_url(self) -> str:
        return f"{self.scheme}://127.0.0.1:{self.port}/"


def compute_pem_sha256(cert_path: str) -> Optional[bytes]:
    if not cert_path or not os.path.isfile(cert_path):
        return None
    try:
        with open(cert_path, "r", encoding="utf-8") as cf:
            pem_text = cf.read()
        match = re.search(r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", pem_text, re.DOTALL)
        if not match:
            return None
        der_bytes = ssl.PEM_cert_to_DER_cert(match.group(0))
        return hashlib.sha256(der_bytes).digest()
    except Exception as exc:
        logger.debug("[CCOBroadcastClient] Could not parse TLS cert pin from %s: %s", cert_path, exc)
        return None


class PinnedHTTPSConnection(http.client.HTTPSConnection):
    """HTTPSConnection enforcing cryptographic cert verification + optional leaf SHA-256 pin."""

    def __init__(
        self,
        host: str,
        port: int,
        timeout: float,
        context: ssl.SSLContext,
        expected_pin_sha256: Optional[bytes],
        server_hostname: str,
    ) -> None:
        super().__init__(host, port=port, timeout=timeout, context=context)
        self._pin_context = context
        self._expected_pin_sha256 = expected_pin_sha256
        self._server_hostname = server_hostname

    def connect(self) -> None:
        sock = self._create_connection((self.host, self.port), self.timeout, self.source_address)
        if getattr(self, "_tunnel_host", None):
            self.sock = sock
            self._tunnel()
        sni_host = self._server_hostname or self.host
        wrapped = self._pin_context.wrap_socket(sock, server_hostname=sni_host)
        if self._expected_pin_sha256 is not None:
            peer_der = wrapped.getpeercert(binary_form=True)
            if not peer_der or not hmac.compare_digest(hashlib.sha256(peer_der).digest(), self._expected_pin_sha256):
                wrapped.close()
                raise ssl.SSLError("CCO gateway TLS certificate pin mismatch")
        self.sock = wrapped


def build_ssl_params(cfg: BroadcastConfig) -> Tuple[Optional[ssl.SSLContext], Optional[bytes]]:
    if cfg.scheme != "https":
        return None, None
    trust_file = (
        cfg.tls_ca
        if (cfg.tls_ca and os.path.isfile(cfg.tls_ca))
        else (cfg.tls_cert if (cfg.tls_cert and os.path.isfile(cfg.tls_cert)) else None)
    )
    ctx = ssl.create_default_context(cafile=trust_file) if trust_file else ssl.create_default_context()
    pin = compute_pem_sha256(cfg.tls_cert)
    if cfg.tls_server_name:
        ctx.check_hostname = True
    elif pin is not None:
        ctx.check_hostname = False
    return ctx, (pin if not cfg.tls_server_name else None)


def open_cco_connection(
    cfg: BroadcastConfig,
    timeout: float,
    ssl_ctx: Optional[ssl.SSLContext],
    pin_sha256: Optional[bytes],
    port_override: Optional[int] = None,
) -> http.client.HTTPConnection:
    port = port_override if (port_override and port_override > 0) else cfg.port
    if cfg.scheme == "https" and ssl_ctx is not None:
        return PinnedHTTPSConnection("127.0.0.1", port, timeout, ssl_ctx, pin_sha256, cfg.tls_server_name)
    return http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
