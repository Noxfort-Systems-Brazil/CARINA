# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Gateway infrastructure backend implementing IRemoteGatewayBackend for UI controllers.
Isolates GoGatewayClient IPC and Tailscale CLI execution inside src/drivers/ (Clean Architecture / DIP).
"""

import logging
from typing import Any, Dict, Optional, Tuple

from src.drivers.go_process_manager import sync_gateway_security_tokens
from src.drivers.tailscale_gateway_adapter import TailscaleGatewayAdapter

logger = logging.getLogger(__name__)


class RemoteGatewayBackend:
    """Adapter bridging TailscaleGatewayAdapter and GoGatewayClient behind IRemoteGatewayBackend."""

    def __init__(
        self,
        go_client: Optional[Any] = None,
        tailscale_adapter: Optional[TailscaleGatewayAdapter] = None,
    ) -> None:
        self._go_client = go_client
        self._tailscale_adapter = tailscale_adapter or TailscaleGatewayAdapter(go_client_provider=self._get_go_client)

    def _get_go_client(self) -> Optional[Any]:
        if self._go_client is None:
            try:
                from src.drivers.go_gateway_client import GoGatewayClient

                self._go_client = GoGatewayClient.get_instance()
            except Exception as exc:
                logger.warning(f"[RemoteGatewayBackend] Falha ao carregar GoGatewayClient: {exc}", exc_info=True)
        return self._go_client

    def is_remote_role(self) -> bool:
        """Returns True when running in remote gateway worker mode (delegates via CentralController)."""
        try:
            from src.drivers.go_gateway_client import GoGatewayClient

            return bool(GoGatewayClient.is_remote_gateway_role())
        except Exception:
            return False

    def detect_domain(self) -> str:
        """Detects active Tailscale MagicDNS domain using the driver CLI adapter."""
        return self._tailscale_adapter.detect_domain()

    def test_connection(self) -> Tuple[bool, str, str]:
        """Tests Tailscale connectivity through Go gateway or falls back to local CLI status."""
        go_client = self._get_go_client()
        if go_client and go_client.is_running():
            res = go_client.send_command("tailscale_status", timeout=8.0)
            if res.get("success", False):
                data = res.get("data") or {}
                dom = TailscaleGatewayAdapter.clean_domain(str(data.get("domain", "")))
                funnel = data.get("funnel_active", False)
                state_str = "Funnel Público Ativo" if funnel else "Conectado"
                return True, f"✅ Tailscale online ({state_str})! Domínio: {dom}", dom
            err = res.get("error", "Tailscale indisponível")
            return False, f"❌ {err}", ""

        domain = self.detect_domain()
        if domain:
            return True, f"✅ Tailscale detectado com sucesso! Domínio: {domain}", domain
        return (
            False,
            "❌ Tailscale não detectado ou desconectado. Certifique-se de que o Tailscale está instalado e autenticado.",
            "",
        )

    def enable_gateway(self, port: int = 2201) -> Tuple[bool, str, str]:
        """Activates Tailscale Funnel CLI and starts the Go WebGatewayServer."""
        self._tailscale_adapter.enable_funnel_cli(port=port)

        go_client = self._get_go_client()
        if go_client:
            go_client.start()
            self.sync_security_tokens()
            go_client.send_command("tailscale_enable", timeout=10.0, port=port)
            go_client.send_command("gateway_set_enabled", timeout=5.0, enabled=True)

        domain = self.detect_domain()
        if domain:
            return True, f"✅ Gateway Tailscale ativo em https://{domain}/cco", domain
        return True, "✅ Gateway Remoto habilitado!", ""

    def disable_gateway(self) -> None:
        """Disables remote access and turns off Tailscale Funnel in Go gateway."""
        go_client = self._get_go_client()
        if go_client and go_client.is_running():
            go_client.send_command("tailscale_disable", timeout=5.0)
            go_client.send_command("gateway_set_enabled", timeout=5.0, enabled=False)
            logger.info("[RemoteGatewayBackend] 🛡️ Gateway Tailscale desativado no backend Go.")

    def get_status(self) -> Dict[str, Any]:
        """Queries real-time status of the Web Gateway from Go process."""
        try:
            go_client = self._get_go_client()
            if go_client and go_client.is_running():
                res = go_client.send_command("gateway_get_status", timeout=2.0)
                if res.get("success", False):
                    return res.get("data", {})
        except Exception as exc:
            logger.debug(f"[RemoteGatewayBackend] Falha ao consultar status do gateway: {exc}")
        return {"enabled": False, "port": 2201}

    def sync_security_tokens(self) -> None:
        """Synchronizes configured EVP/CCO auth tokens and CORS origin with Go gateway."""
        try:
            go_client = self._get_go_client()
            if go_client and go_client.is_running():
                sync_gateway_security_tokens(go_client)
        except Exception as exc:
            logger.debug(f"[RemoteGatewayBackend] Aviso ao sincronizar tokens no Go Gateway: {exc}")

    def sync_enabled_state(self, enabled: bool) -> None:
        """Synchronizes enabled flag and security tokens inside running Go gateway process."""
        try:
            go_client = self._get_go_client()
            if go_client and go_client.is_running():
                self.sync_security_tokens()
                go_client.send_command("gateway_set_enabled", timeout=5.0, enabled=bool(enabled))
        except Exception as exc:
            logger.debug(f"[RemoteGatewayBackend] Aviso ao sincronizar Go Gateway: {exc}")
