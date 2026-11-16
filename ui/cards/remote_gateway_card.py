# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Remote Gateway Configuration Card (Tailscale Funnel / CCO / EVP).
Acts strictly as a pure View (Clean Architecture), delegating business logic
to RemoteGatewayController and form layout to RemoteGatewayFormControls (SRP + DIP).
"""

import logging
from typing import Any, Callable, Dict, Optional

import flet as ft

from ui.components.remote_endpoints_banner import RemoteEndpointsBanner
from ui.components.remote_gateway_form import RemoteGatewayFormControls
from ui.controllers.remote_gateway_controller import RemoteGatewayController
from ui.handlers.locale_manager import LocaleManager

logger = logging.getLogger(__name__)


class RemoteGatewayCard(ft.Card):
    """UI Card encapsulating Tailscale Funnel, CCO, and EVP Remote Access interface."""

    def __init__(
        self,
        initial_values: Dict[str, Any],
        on_toggle_connection: Optional[Callable[[bool, Dict[str, Any]], None]] = None,
        locale_manager: Optional[LocaleManager] = None,
        controller: Optional[RemoteGatewayController] = None,
    ):
        super().__init__()
        self.elevation = 2
        self.lm = locale_manager
        self.controller = controller or RemoteGatewayController()
        self.on_toggle_connection = on_toggle_connection

        is_enabled_raw = initial_values.get("gateway_enabled", False)
        self.is_connected = str(is_enabled_raw).lower() in ("true", "1", "t")
        self._initial_connected = self.is_connected

        # Visual Endpoints Subcomponent
        urls = self.controller.format_service_urls()
        self.connection_banner = RemoteEndpointsBanner(
            initial_cco_url=urls["cco_url"],
            initial_evp_url=urls["evp_url"],
            on_copy=self._copy_to_clipboard,
            on_open_url=self._open_in_browser,
        )

        # Decoupled form controls assembly (SRP)
        self._form = RemoteGatewayFormControls(
            is_connected=self.is_connected,
            on_test_click=self._handle_test_connection,
            on_connect_click=self._handle_connect,
            on_disconnect_click=self._handle_disconnect,
        )

        # Property exposure for compatibility
        self.title_text = self._form.title_text
        self.status_icon = self._form.status_icon
        self.status_text = self._form.status_text
        self.status_display = self._form.status_display
        self.btn_test = self._form.btn_test
        self.btn_connect = self._form.btn_connect
        self.btn_disconnect = self._form.btn_disconnect

        self.content = self._form.build_layout(self.connection_banner)

    # Handlers & Visual Synchronization
    def _update_urls_display(self, e=None):
        urls = self.controller.format_service_urls()
        self.connection_banner.update_urls(urls["cco_url"], urls["evp_url"])

    def _open_in_browser(self, url: str):
        """Opens URL directly in default system browser."""
        try:
            import webbrowser

            webbrowser.open(url)
            self._show_snackbar("Abrindo CCO no navegador...", ft.Colors.GREEN_700, ft.Icons.OPEN_IN_BROWSER_ROUNDED)
        except Exception as ex:
            self._show_snackbar(f"Erro ao abrir navegador: {ex}", ft.Colors.RED_700, ft.Icons.ERROR_ROUNDED)

    def _show_snackbar(self, text: str, color: Any, icon_name: Optional[str] = None):
        if not self.page:
            return
        content_items = []
        if icon_name:
            content_items.append(ft.Icon(icon_name, color=ft.Colors.WHITE, size=18))
        content_items.append(ft.Text(text, color=ft.Colors.WHITE))

        self.page.snack_bar = ft.SnackBar(
            content=ft.Row(content_items, spacing=8),
            bgcolor=color,
            duration=3000,
        )
        self.page.snack_bar.open = True
        self.page.update()

    def _copy_to_clipboard(self, text: str, label: str):
        """Copies URL to clipboard with validation and feedback."""
        if "<seu-dominio>" in text and "localhost" not in text:
            self._show_snackbar(
                "Conecte sua conta Tailscale antes de copiar o link remoto.",
                ft.Colors.AMBER_900,
                ft.Icons.WARNING_AMBER_ROUNDED,
            )
            return

        if self.page:
            self.page.set_clipboard(text)
            self._show_snackbar(f"{label} copiado: {text}", ft.Colors.GREEN_700, ft.Icons.CHECK_CIRCLE)
            logger.info(f"[RemoteGatewayCard] {label} copiado para clipboard: {text}")

    def _update_ui_state(self):
        """Synchronizes enablement state and visibility of controls."""
        self._form.apply_connection_state(self.is_connected)
        self._update_urls_display()
        if self.page:
            self.update()

    def _handle_test_connection(self, e):
        """Delegates Tailscale status check to the controller."""

        def _on_test_result(success: bool, msg: str):
            self._update_urls_display()
            color = ft.Colors.GREEN_700 if success else ft.Colors.RED_700
            self._show_snackbar(msg, color)

        self.controller.test_connection_async(on_result=_on_test_result)

    def _handle_connect(self, e):
        """Enables Tailscale Funnel and remote gateway via controller."""
        self.is_connected = True
        self._update_ui_state()

        def _on_connect_result(success: bool, msg: str):
            self._update_urls_display()
            color = ft.Colors.GREEN_700 if success else ft.Colors.RED_700
            self._show_snackbar(msg, color, ft.Icons.CHECK_CIRCLE if success else ft.Icons.ERROR_ROUNDED)

        self.controller.connect_gateway_async(on_result=_on_connect_result)

        if self.on_toggle_connection:
            self.on_toggle_connection(True, self.get_values())

    def _handle_disconnect(self, e):
        """Disconnects Tailscale Funnel via controller."""
        self.is_connected = False
        self._update_ui_state()

        self.controller.disconnect_gateway()

        if self.on_toggle_connection:
            self.on_toggle_connection(False, self.get_values())

        self._show_snackbar("Gateway Remoto desativado.", ft.Colors.RED_700, ft.Icons.POWER_SETTINGS_NEW)

    def handle_remote_response(self, payload: Dict[str, Any]) -> None:
        """Handles asynchronous Tailscale gateway responses forwarded by CentralController."""
        if hasattr(self.controller, "handle_remote_response"):
            self.controller.handle_remote_response(payload)
        self._update_urls_display()

    # Public API / Persistence
    def set_values(self, settings: Dict[str, Any]):
        """Updates card controls from settings dictionary."""
        is_enabled_raw = settings.get("gateway_enabled", False)
        self.is_connected = str(is_enabled_raw).lower() in ("true", "1", "t")
        self._initial_connected = self.is_connected
        self._update_ui_state()

    def update_translations(self, lm: LocaleManager):
        self.lm = lm

    def get_values(self) -> Dict[str, Any]:
        """Returns current card values for persistence."""
        return {
            "gateway_enabled": self.is_connected,
        }

    def has_unsaved_changes(self) -> bool:
        return self.is_connected != self._initial_connected

    def save_changes(self) -> None:
        self.controller.persist_settings(gateway_enabled=self.is_connected)
        self._initial_connected = self.is_connected

    def discard_changes(self) -> None:
        self.is_connected = self._initial_connected
        self._update_ui_state()
