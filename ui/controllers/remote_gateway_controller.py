# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Remote Access and Web Gateway Controller (SOLID - Clean Architecture).
Orchestrates automatic Tailscale Funnel detection, asynchronous command execution
to the Go Gateway, and settings persistence (.env / settings.ini).
Decoupled from Flet UI framework components (DIP).
"""

import json
import logging
import subprocess
import threading
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class RemoteGatewayController:
    """Controller orchestrating Tailscale Remote Gateway business logic for presentation layer."""

    def __init__(
        self,
        go_client: Any = None,
        settings_manager: Any = None,
        env_provider: Any = None,
    ):
        self._go_client = go_client
        self._settings_manager = settings_manager
        self._env_provider = env_provider
        self._cached_domain: Optional[str] = None
        self.is_busy = False

    def _get_go_client(self):
        if self._go_client is None:
            try:
                from src.drivers.go_gateway_client import GoGatewayClient
                self._go_client = GoGatewayClient.get_instance()
            except Exception as e:
                logger.warning(f"[RemoteGatewayController] Falha ao carregar GoGatewayClient: {e}", exc_info=True)
        return self._go_client

    def _get_settings_manager(self):
        if self._settings_manager is None:
            from src.utils.settings_manager import SettingsManager
            self._settings_manager = SettingsManager()
        return self._settings_manager

    def _get_env_provider(self):
        if self._env_provider is None:
            try:
                from src.settings.env_provider import DotenvSecretProvider
                self._env_provider = DotenvSecretProvider()
            except Exception:
                pass
        return self._env_provider

    def clean_domain(self, domain_raw: str) -> str:
        """Cleans and formats Tailscale domain removing protocols, slashes and trailing dots."""
        d = (domain_raw or "").strip()
        for prefix in ("https://", "http://"):
            if d.startswith(prefix):
                d = d[len(prefix):]
        return d.rstrip("/.")

    def detect_tailscale_domain(self) -> str:
        """Automatically queries local Tailscale daemon for active MagicDNS domain."""
        if self._cached_domain:
            return self._cached_domain

        try:
            proc = subprocess.run(
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
                    self._cached_domain = self.clean_domain(cert_domains[0])
                    return self._cached_domain
                self_node = data.get("Self") or {}
                dns_name = self_node.get("DNSName", "")
                if dns_name:
                    self._cached_domain = self.clean_domain(dns_name)
                    return self._cached_domain
        except Exception as e:
            logger.debug(f"[RemoteGatewayController] Não foi possível detectar domínio Tailscale via CLI: {e}")

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

    def test_connection_async(
        self,
        on_result: Callable[[bool, str], None],
    ) -> None:
        """Verifies Tailscale daemon and Funnel status in background."""
        def _do_test():
            self.is_busy = True
            try:
                go_client = self._get_go_client()
                if go_client and go_client.is_running():
                    res = go_client.send_command("tailscale_status", timeout=8.0)
                    if res.get("success", False):
                        data = res.get("data") or {}
                        dom = data.get("domain", "")
                        if dom:
                            self._cached_domain = self.clean_domain(dom)
                        funnel = data.get("funnel_active", False)
                        state_str = "Funnel Público Ativo" if funnel else "Conectado"
                        on_result(True, f"✅ Tailscale online ({state_str})! Domínio: {dom}")
                        return
                    else:
                        err = res.get("error", "Tailscale indisponível")
                        on_result(False, f"❌ {err}")
                        return

                # Fallback check directly via CLI if Go Gateway is not yet running
                domain = self.detect_tailscale_domain()
                if domain:
                    on_result(True, f"✅ Tailscale detectado com sucesso! Domínio: {domain}")
                else:
                    on_result(
                        False,
                        "❌ Tailscale não detectado ou desconectado. Certifique-se de que o Tailscale está instalado e autenticado.",
                    )
            except Exception as ex:
                logger.error(f"[RemoteGatewayController] Erro ao verificar Tailscale: {ex}", exc_info=True)
                on_result(False, f"Erro ao verificar status do Tailscale: {ex}")
            finally:
                self.is_busy = False

        threading.Thread(target=_do_test, daemon=True, name="TailscaleTestThread").start()

    def connect_gateway_async(
        self,
        on_result: Callable[[bool, str], None],
    ) -> None:
        """Starts Go Gateway and automatically enables Tailscale Funnel on port 2201 in background."""
        def _do_connect():
            self.is_busy = True
            try:
                # 1. Ensure local Tailscale Funnel is active on port 2201
                try:
                    subprocess.run(
                        ["tailscale", "funnel", "--bg", "2201"],
                        capture_output=True,
                        text=True,
                        timeout=10.0,
                        check=False,
                    )
                except Exception as cli_err:
                    logger.debug(f"[RemoteGatewayController] Aviso ao ativar funnel via CLI: {cli_err}")

                # 2. Start and enable Go WebGatewayServer
                go_client = self._get_go_client()
                if go_client:
                    go_client.start()
                    go_client.send_command("tailscale_enable", timeout=10.0, port=2201)
                    go_client.send_command("gateway_set_enabled", timeout=5.0, enabled=True)

                domain = self.detect_tailscale_domain()
                if domain:
                    on_result(True, f"✅ Gateway Tailscale ativo em https://{domain}/cco")
                else:
                    on_result(True, "✅ Gateway Remoto habilitado!")
            except Exception as ex:
                logger.warning(f"[RemoteGatewayController] Falha ao ativar Gateway Tailscale: {ex}", exc_info=True)
                on_result(False, f"Falha ao ativar Gateway Tailscale: {ex}")
            finally:
                self.is_busy = False

        threading.Thread(target=_do_connect, daemon=True, name="TailscaleConnectThread").start()

    def disconnect_gateway(self) -> None:
        """Disables remote access immediately on Go backend and turns off Tailscale Funnel."""
        try:
            go_client = self._get_go_client()
            if go_client and go_client.is_running():
                go_client.send_command("tailscale_disable", timeout=5.0)
                go_client.send_command("gateway_set_enabled", timeout=5.0, enabled=False)
                logger.info("[RemoteGatewayController] 🛡️ Gateway Tailscale desativado no backend Go.")
        except Exception as e:
            logger.warning(f"[RemoteGatewayController] Erro ao desativar gateway no Go: {e}", exc_info=True)

    def get_gateway_status(self) -> Dict[str, Any]:
        """Queries real-time status of Web Gateway in Go process."""
        try:
            go_client = self._get_go_client()
            if go_client and go_client.is_running():
                res = go_client.send_command("gateway_get_status", timeout=2.0)
                if res.get("success", False):
                    return res.get("data", {})
        except Exception as e:
            logger.debug(f"[RemoteGatewayController] Falha ao consultar status do gateway: {e}")
        return {"enabled": False, "port": 2201}

    def persist_settings(self, gateway_enabled: bool) -> None:
        """Immediately saves gateway_enabled state in settings.ini, .env and Go process."""
        try:
            # 1. Persist directly to config/settings.ini via SettingsHandler
            from ui.handlers.settings_handler import SettingsHandler
            sh = SettingsHandler()
            sh.save_to_file({
                "gateway_enabled": gateway_enabled,
            })
            if hasattr(sh, "_cached_settings") and sh._cached_settings is not None:
                sh._cached_settings.update({
                    "gateway_enabled": gateway_enabled,
                })

            # 2. Synchronize via SettingsManager if available
            try:
                sm = self._get_settings_manager()
                if sm:
                    curr = sm.load_settings()
                    curr["gateway_enabled"] = gateway_enabled
                    sm.save_settings(curr)
            except Exception:
                pass

            # 3. Synchronize CARINA_GATEWAY_ENABLED with .env file
            env_provider = self._get_env_provider()
            if env_provider:
                try:
                    env_provider.sync_variable("CARINA_GATEWAY_ENABLED", str(gateway_enabled))
                except Exception as env_err:
                    logger.debug(f"[RemoteGatewayController] Erro ao sincronizar .env: {env_err}")

            # 4. Immediately synchronize enabled state in running Go process
            try:
                go_client = self._get_go_client()
                if go_client and go_client.is_running():
                    go_client.send_command(
                        "gateway_set_enabled",
                        timeout=5.0,
                        enabled=gateway_enabled,
                    )
            except Exception as sync_go_err:
                logger.debug(f"[RemoteGatewayController] Aviso ao sincronizar Go Gateway: {sync_go_err}")

            logger.info(f"[RemoteGatewayController] Configurações persistidas com sucesso: enabled={gateway_enabled}")
        except Exception as err:
            logger.error(f"[RemoteGatewayController] Falha ao persistir configurações: {err}", exc_info=True)
