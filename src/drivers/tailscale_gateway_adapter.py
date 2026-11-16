# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Infrastructure adapter for Tailscale Funnel CLI and Go gateway Tailscale RPC commands.
Keeps OS subprocess invocation and protocol transport formatting outside the Controller layer.
"""

import json
import logging
import subprocess
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class TailscaleGatewayAdapter:
    """Executes Tailscale status/enable/disable operations across OS CLI and GoGatewayClient."""

    @staticmethod
    def clean_domain(domain_raw: str) -> str:
        """Normalizes a Tailscale MagicDNS domain by stripping scheme, slashes, and trailing dots."""
        cleaned = (domain_raw or "").strip()
        for prefix in ("https://", "http://"):
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix) :]
        return cleaned.rstrip("/.")

    def __init__(
        self,
        go_client_provider: Optional[Callable[[], Optional[Any]]] = None,
        locale_manager: Optional[Any] = None,
        subprocess_runner: Callable[..., Any] = subprocess.run,
    ) -> None:
        self._go_client_provider = go_client_provider
        self.locale_manager = locale_manager
        self._subprocess_runner = subprocess_runner
        self._handlers: Dict[str, Callable[[Optional[Dict[str, Any]], Dict[str, Any]], None]] = {
            "tailscale_test": self._handle_test,
            "tailscale_enable": self._handle_enable,
            "tailscale_disable": self._handle_disable,
        }

    def _msg(self, key: str, default: str, **kwargs: Any) -> str:
        if self.locale_manager is not None and hasattr(self.locale_manager, "get_string"):
            try:
                return self.locale_manager.get_string(key, default=default, **kwargs)
            except Exception:
                pass
        try:
            return default.format(**kwargs) if kwargs else default
        except Exception:
            return default

    def _resolve_go_client(self) -> Optional[Any]:
        return self._go_client_provider() if self._go_client_provider is not None else None

    def detect_domain(self) -> str:
        """Queries the local Tailscale CLI (`tailscale status --json`) for the MagicDNS domain."""
        try:
            proc = self._subprocess_runner(
                ["tailscale", "status", "--json"],
                capture_output=True,
                text=True,
                timeout=2.5,
                check=False,
            )
            if proc.returncode == 0 and proc.stdout:
                data = json.loads(proc.stdout)
                cert_domains = data.get("CertDomains") or []
                if cert_domains:
                    return self.clean_domain(str(cert_domains[0]))
                self_node = data.get("Self") or {}
                dns_name = self_node.get("DNSName", "")
                if dns_name:
                    return self.clean_domain(str(dns_name))
        except Exception as exc:
            logger.debug(f"[TailscaleGatewayAdapter] Failed to detect Tailscale domain via CLI: {exc}")
        return ""

    def enable_funnel_cli(self, port: int = 2201) -> None:
        """Attempts to activate local Tailscale Funnel via CLI before starting the Go gateway."""
        try:
            self._subprocess_runner(
                ["tailscale", "funnel", "--bg", str(int(port))],
                capture_output=True,
                text=True,
                timeout=10.0,
                check=False,
            )
        except Exception as exc:
            logger.debug(f"[TailscaleGatewayAdapter] OS tailscale funnel invocation note: {exc}")

    def execute(self, cmd_type: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Dispatches a Tailscale command via table lookup and returns normalized UI response metadata."""
        response: Dict[str, Any] = {"action": cmd_type, "success": False, "message": "", "domain": ""}
        handler = self._handlers.get(cmd_type)
        if handler is None:
            response["message"] = f"Unknown Tailscale command '{cmd_type}'"
            return response

        try:
            handler(payload, response)
        except Exception as exc:
            response.update(success=False, message=f"Falha no comando Tailscale '{cmd_type}': {exc}")
        return response

    def _handle_test(self, _payload: Optional[Dict[str, Any]], response: Dict[str, Any]) -> None:
        go_client = self._resolve_go_client()
        if not go_client or not go_client.is_running():
            response.update(
                success=False,
                message=self._msg(
                    "remote_gateway.go_unavailable",
                    "❌ Gateway Go indisponível para testar Tailscale.",
                ),
            )
            return

        res = go_client.send_command("tailscale_status", timeout=8.0)
        data = res.get("data") or {}
        dom = str(data.get("domain", ""))
        if not res.get("success", False):
            response.update(success=False, message=f"❌ {res.get('error', 'Tailscale indisponível')}")
            return

        funnel = data.get("funnel_active", False)
        state_str = "Funnel Público Ativo" if funnel else "Conectado"
        response.update(
            success=True,
            domain=dom,
            message=self._msg(
                "remote_gateway.online_status",
                "✅ Tailscale online ({state_str})! Domínio: {dom}",
                state_str=state_str,
                dom=dom,
            ),
        )

    def _handle_enable(self, payload: Optional[Dict[str, Any]], response: Dict[str, Any]) -> None:
        port = int((payload or {}).get("port", 2201))
        self.enable_funnel_cli(port=port)

        go_client = self._resolve_go_client()
        if not go_client:
            response.update(
                success=False,
                message=self._msg("remote_gateway.client_unavailable", "❌ GoGatewayClient indisponível."),
            )
            return

        go_client.start()
        go_client.send_command("tailscale_enable", timeout=10.0, port=port)
        go_client.send_command("gateway_set_enabled", timeout=5.0, enabled=True)
        st = go_client.send_command("tailscale_status", timeout=5.0)
        dom = str((st.get("data") or {}).get("domain", "")) if isinstance(st, dict) else ""
        message = f"✅ Gateway Tailscale ativo em https://{dom}/cco" if dom else "✅ Gateway Remoto habilitado!"
        response.update(success=True, domain=dom, message=message)

    def _handle_disable(self, _payload: Optional[Dict[str, Any]], response: Dict[str, Any]) -> None:
        go_client = self._resolve_go_client()
        if go_client and go_client.is_running():
            go_client.send_command("tailscale_disable", timeout=5.0)
            go_client.send_command("gateway_set_enabled", timeout=5.0, enabled=False)
        response.update(
            success=True,
            message=self._msg(
                "remote_gateway.disabled",
                "🛡️ Gateway Tailscale desativado no backend Go.",
            ),
        )
