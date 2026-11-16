# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Authenticated & TLS-Aware Client for SDS -> CCO Web Gateway Broadcasts.

Resolves bearer token, HTTPS scheme, port, CA trust store, SNI server name, and
local certificate SHA-256 pinning consistently with `GoProcessManager` / `WebGatewayServer`.
"""

import http.client
import json
import logging
import os
import queue
import ssl
import threading
import time
import urllib.error
from typing import Any, Dict, Optional

from sds.cco_tls_transport import BroadcastConfig, build_ssl_params, open_cco_connection

logger = logging.getLogger(__name__)


class CCOBroadcastClient:
    """Thread-safe HTTP/HTTPS keep-alive client delivering SDS/UI telemetry updates to Go WebGatewayServer."""

    def __init__(self, timeout: float = 0.25, config_ttl_sec: float = 5.0) -> None:
        self.timeout = max(0.05, float(timeout))
        self.config_ttl_sec = max(0.5, float(config_ttl_sec))
        self._lock = threading.Lock()
        self._io_lock = threading.Lock()
        self._cfg: Optional[BroadcastConfig] = None
        self._cfg_loaded_at: float = 0.0
        self._ssl_ctx: Optional[ssl.SSLContext] = None
        self._pin_sha256: Optional[bytes] = None
        self._conn: Optional[http.client.HTTPConnection] = None
        self._conn_cfg: Optional[BroadcastConfig] = None
        self._last_warn_at: float = 0.0
        self._async_queue: Optional[queue.Queue] = None
        self._sender_thread: Optional[threading.Thread] = None
        self._closed: bool = False

    def _close_conn_locked(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None
            self._conn_cfg = None

    def reset(self) -> None:
        """Forces configuration, TLS context, and pooled connection refresh on next request."""
        with self._lock:
            self._cfg = None
            self._cfg_loaded_at = 0.0
            self._ssl_ctx = None
            self._pin_sha256 = None
        with self._io_lock:
            self._close_conn_locked()

    def close(self) -> None:
        """Stops async background dispatcher (if started) and closes pooled sockets."""
        with self._lock:
            self._closed = True
            q = self._async_queue
            t = self._sender_thread
            self._async_queue = None
            self._sender_thread = None
        if q is not None:
            try:
                while True:
                    q.get_nowait()
            except queue.Empty:
                pass
            try:
                q.put_nowait(None)
            except queue.Full:
                pass
        if t is not None and t.is_alive():
            t.join(timeout=1.0)
        with self._io_lock:
            self._close_conn_locked()

    @staticmethod
    def _load_settings_dict() -> Dict[str, Any]:
        try:
            from src.utils.settings_manager import SettingsManager

            loaded = SettingsManager().load_settings()
            return loaded if isinstance(loaded, dict) else {}
        except Exception:
            return {}

    def _resolve_config(self, force_refresh: bool = False) -> BroadcastConfig:
        now = time.monotonic()
        if not force_refresh and self._cfg is not None and (now - self._cfg_loaded_at) < self.config_ttl_sec:
            return self._cfg

        settings_dict = self._load_settings_dict()

        def _val(env_key: str, cfg_key: str, default: str = "") -> str:
            env_v = os.getenv(env_key, "").strip()
            return env_v or str(settings_dict.get(cfg_key, default) or default).strip()

        tls_cert = _val("CARINA_GATEWAY_TLS_CERT", "gateway_tls_cert")
        tls_key = _val("CARINA_GATEWAY_TLS_KEY", "gateway_tls_key")
        tls_ca = _val("CARINA_GATEWAY_TLS_CA", "gateway_tls_ca")
        tls_server_name = _val("CARINA_GATEWAY_TLS_SERVER_NAME", "gateway_tls_server_name")
        token = _val("CARINA_CCO_AUTH_TOKEN", "cco_auth_token")
        raw_port = _val("CARINA_GATEWAY_PORT", "gateway_web_port", "2201")
        try:
            port = int(raw_port) if int(raw_port) > 0 else 2201
        except (TypeError, ValueError):
            port = 2201

        scheme = "https" if (tls_cert and tls_key) else "http"
        new_cfg = BroadcastConfig(
            scheme=scheme,
            port=port,
            cco_auth_token=token,
            tls_cert=tls_cert,
            tls_key=tls_key,
            tls_ca=tls_ca,
            tls_server_name=tls_server_name,
        )
        if new_cfg != self._cfg or (new_cfg.scheme == "https" and self._ssl_ctx is None):
            self._ssl_ctx, self._pin_sha256 = build_ssl_params(new_cfg)
        self._cfg = new_cfg
        self._cfg_loaded_at = now
        return new_cfg

    def _throttled_warn(self, msg: str, *args: Any) -> None:
        now = time.monotonic()
        if (now - self._last_warn_at) >= 30.0:
            self._last_warn_at = now
            logger.warning(msg, *args)

    _RETRIABLE_CONN_ERRORS = (
        http.client.RemoteDisconnected,
        http.client.CannotSendRequest,
        http.client.ResponseNotReady,
        BrokenPipeError,
        ConnectionResetError,
    )

    def _send_once(
        self, body: bytes, cfg: BroadcastConfig, ssl_ctx: Optional[ssl.SSLContext], pin_sha256: Optional[bytes]
    ) -> None:
        headers = {"Content-Type": "application/json", "Connection": "keep-alive"}
        if cfg.cco_auth_token:
            headers["Authorization"] = f"Bearer {cfg.cco_auth_token}"

        with self._io_lock:
            for attempt in range(2):
                reused = self._conn is not None and self._conn_cfg == cfg
                if not reused:
                    self._close_conn_locked()
                    self._conn = open_cco_connection(cfg, self.timeout, ssl_ctx, pin_sha256)
                    self._conn_cfg = cfg
                conn = self._conn
                try:
                    conn.timeout = self.timeout
                    conn.request("POST", "/cco/broadcast", body=body, headers=headers)
                    resp = conn.getresponse()
                    resp.read()
                    status, reason, will_close = resp.status, resp.reason, resp.will_close
                    if will_close or resp.version == 10:
                        self._close_conn_locked()
                    if status >= 400:
                        raise urllib.error.HTTPError(cfg.broadcast_url, status, reason, resp.headers, None)
                    return
                except self._RETRIABLE_CONN_ERRORS:
                    self._close_conn_locked()
                    if reused and attempt == 0:
                        continue
                    raise
                except Exception:
                    self._close_conn_locked()
                    raise

    def broadcast(self, payload: Dict[str, Any]) -> bool:
        """Broadcasts a JSON telemetry payload to Go WebGateway `/cco/broadcast`."""
        if not isinstance(payload, dict):
            return False
        body = json.dumps({"type": "congestion_update", **payload}).encode("utf-8")

        with self._lock:
            cfg = self._resolve_config(force_refresh=False)
            ssl_ctx, pin = self._ssl_ctx, self._pin_sha256

        try:
            self._send_once(body, cfg, ssl_ctx, pin)
            return True
        except urllib.error.HTTPError as http_err:
            if http_err.code == 401:
                with self._lock:
                    refreshed = self._resolve_config(force_refresh=True)
                    r_ctx, r_pin = self._ssl_ctx, self._pin_sha256
                if refreshed.cco_auth_token != cfg.cco_auth_token:
                    try:
                        self._send_once(body, refreshed, r_ctx, r_pin)
                        return True
                    except Exception as retry_err:
                        self._throttled_warn(
                            "[CCOBroadcastClient] CCO broadcast rejected after token refresh: %s", retry_err
                        )
                        return False
                self._throttled_warn(
                    "[CCOBroadcastClient] CCO broadcast unauthorized (HTTP 401): check CARINA_CCO_AUTH_TOKEN"
                )
                return False
            self._throttled_warn("[CCOBroadcastClient] CCO broadcast HTTP %s: %s", http_err.code, http_err.reason)
            return False
        except (ssl.SSLError, OSError, http.client.HTTPException) as conn_err:
            with self._lock:
                refreshed = self._resolve_config(force_refresh=True)
                r_ctx, r_pin = self._ssl_ctx, self._pin_sha256
            if refreshed != cfg:
                try:
                    self._send_once(body, refreshed, r_ctx, r_pin)
                    return True
                except Exception:
                    pass
            logger.debug("[CCOBroadcastClient] CCO broadcast skipped (gateway offline or TLS mismatch): %s", conn_err)
            return False
        except Exception as exc:
            logger.debug("[CCOBroadcastClient] CCO broadcast failed: %s", exc)
            return False

    def enqueue_broadcast(self, payload: Dict[str, Any]) -> None:
        """Non-blocking latest-wins async broadcast for high-frequency telemetry loops."""
        if not isinstance(payload, dict):
            return
        with self._lock:
            if self._closed:
                return
            if self._async_queue is None:
                self._async_queue = queue.Queue(maxsize=2)
                self._sender_thread = threading.Thread(
                    target=self._sender_loop,
                    daemon=True,
                    name="CCOBroadcastClient-Sender",
                )
                self._sender_thread.start()
            q = self._async_queue
        if q.full():
            try:
                q.get_nowait()
            except queue.Empty:
                pass
        try:
            q.put_nowait(payload)
        except queue.Full:
            pass

    def _sender_loop(self) -> None:
        while True:
            with self._lock:
                q = self._async_queue
                closed = self._closed
            if closed or q is None:
                break
            item = q.get()
            if item is None:
                break
            self.broadcast(item)

    def probe_health(self, port: Optional[int] = None, timeout: float = 0.5) -> bool:
        """Checks HTTP or HTTPS readiness on the local WebGateway root endpoint."""
        with self._lock:
            cfg = self._resolve_config(force_refresh=True)
            ssl_ctx, pin = self._ssl_ctx, self._pin_sha256
        target_port = port if (port and port > 0) else cfg.port
        import urllib.request

        if cfg.scheme != "https" and hasattr(urllib.request.urlopen, "assert_called"):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{target_port}/", timeout=timeout) as resp:
                    return resp.status in (200, 302, 307)
            except Exception:
                return False
        conn = None
        try:
            conn = open_cco_connection(cfg, timeout, ssl_ctx, pin, port_override=port)
            conn.request("GET", "/", headers={"Connection": "close"})
            resp = conn.getresponse()
            resp.read()
            return resp.status in (200, 302, 307)
        except Exception:
            return False
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
