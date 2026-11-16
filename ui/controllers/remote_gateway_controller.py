# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Remote Access and Web Gateway Presentation Controller (SOLID - Clean Architecture).
Orchestrates URL formatting, async execution state, and IPC callback correlation for the UI,
delegating OS/Go operations to IRemoteGatewayBackend and persistence to IGatewaySettingsPersister (DIP).
"""

import logging
import threading
from typing import Any, Callable, Dict, Optional

from src.drivers.remote_gateway_backend import RemoteGatewayBackend
from src.drivers.tailscale_gateway_adapter import TailscaleGatewayAdapter
from src.interfaces.controller import IGatewaySettingsPersister, IRemoteGatewayBackend
from ui.controllers.remote_gateway_settings_persister import RemoteGatewaySettingsPersister

logger = logging.getLogger(__name__)


class RemoteGatewayController:
    """Thin presentation controller orchestrating Tailscale Remote Gateway UI workflows."""

    def __init__(
        self,
        go_client: Any = None,
        settings_manager: Any = None,
        env_provider: Any = None,
        settings_client: Any = None,
        backend: Optional[IRemoteGatewayBackend] = None,
        persister: Optional[IGatewaySettingsPersister] = None,
    ):
        self._settings_client = settings_client
        self._backend: IRemoteGatewayBackend = backend or RemoteGatewayBackend(go_client=go_client)
        self._persister: IGatewaySettingsPersister = persister or RemoteGatewaySettingsPersister(
            settings_manager=settings_manager,
            env_provider=env_provider,
        )
        self._cached_domain: Optional[str] = None
        self._pending_callbacks: Dict[str, Callable[[bool, str], None]] = {}
        self.is_busy = False

    def handle_remote_response(self, payload: Dict[str, Any]) -> None:
        """Applies async Tailscale result received from CentralController via SDS/IPC."""
        if not isinstance(payload, dict):
            return
        dom = payload.get("domain", "")
        if dom:
            self._cached_domain = self.clean_domain(str(dom))
        action = str(payload.get("action", ""))
        success = bool(payload.get("success", False))
        msg = str(payload.get("message", ""))
        cb = self._pending_callbacks.pop(action, None)
        if cb and msg:
            cb(success, msg)

    def clean_domain(self, domain_raw: str) -> str:
        """Cleans and formats Tailscale domain removing protocols, slashes and trailing dots."""
        return TailscaleGatewayAdapter.clean_domain(domain_raw)

    def detect_tailscale_domain(self) -> str:
        """Queries active MagicDNS domain via injected backend adapter (with in-memory cache)."""
        if self._cached_domain:
            return self._cached_domain
        detected = self._backend.detect_domain()
        if detected:
            self._cached_domain = self.clean_domain(detected)
            return self._cached_domain
        return ""

    def format_service_urls(self, domain_raw: str = "") -> Dict[str, str]:
        """Generates ready-to-use URLs for CCO and EVP services via Tailscale Funnel."""
        domain = self.clean_domain(domain_raw)
        if not domain:
            domain = self.detect_tailscale_domain()

        display_domain = domain if domain else "<seu-dominio>.ts.net"
        return {
            "domain": domain,
            "cco_url": f"https://{display_domain}/cco",
            "evp_url": f"https://{display_domain}/amb/v1",
        }

    def _dispatch_remote_ipc(
        self,
        cmd: str,
        payload: Dict[str, Any],
        on_result: Optional[Callable[[bool, str], None]] = None,
    ) -> bool:
        if self._settings_client is not None and self._backend.is_remote_role():
            if on_result is not None:
                self._pending_callbacks[cmd] = on_result
            self._settings_client.send_command(cmd, payload)
            return True
        return False

    def test_connection_async(self, on_result: Callable[[bool, str], None]) -> None:
        """Verifies Tailscale daemon and Funnel status in background."""
        if self._dispatch_remote_ipc("tailscale_test", {}, on_result=on_result):
            return

        def _do_test():
            self.is_busy = True
            try:
                ok, msg, dom = self._backend.test_connection()
                if dom:
                    self._cached_domain = self.clean_domain(dom)
                on_result(ok, msg)
            except Exception as ex:
                logger.error(f"[RemoteGatewayController] Erro ao verificar Tailscale: {ex}", exc_info=True)
                on_result(False, f"Erro ao verificar status do Tailscale: {ex}")
            finally:
                self.is_busy = False

        threading.Thread(target=_do_test, daemon=True, name="TailscaleTestThread").start()

    def connect_gateway_async(self, on_result: Callable[[bool, str], None]) -> None:
        """Starts Go Gateway and activates Tailscale Funnel on port 2201 in background."""
        if self._dispatch_remote_ipc("tailscale_enable", {"port": 2201}, on_result=on_result):
            return

        def _do_connect():
            self.is_busy = True
            try:
                ok, msg, dom = self._backend.enable_gateway(port=2201)
                if dom:
                    self._cached_domain = self.clean_domain(dom)
                on_result(ok, msg)
            except Exception as ex:
                logger.warning(f"[RemoteGatewayController] Falha ao ativar Gateway Tailscale: {ex}", exc_info=True)
                on_result(False, f"Falha ao ativar Gateway Tailscale: {ex}")
            finally:
                self.is_busy = False

        threading.Thread(target=_do_connect, daemon=True, name="TailscaleConnectThread").start()

    def disconnect_gateway(self) -> None:
        """Disables remote access immediately on Go backend and turns off Tailscale Funnel."""
        try:
            if self._dispatch_remote_ipc("tailscale_disable", {}):
                return
            self._backend.disable_gateway()
        except Exception as exc:
            logger.warning(f"[RemoteGatewayController] Erro ao desativar gateway no Go: {exc}", exc_info=True)

    def get_gateway_status(self) -> Dict[str, Any]:
        """Queries real-time status of Web Gateway in Go process."""
        return self._backend.get_status()

    def persist_settings(self, gateway_enabled: bool) -> None:
        """Delegates gateway_enabled persistence across INI, .env, and backend."""
        self._persister.persist(gateway_enabled, backend=self._backend)
