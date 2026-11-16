# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import flet as ft


class NetworkEventHandler:
    """
    Orchestrator and router responsible for receiving raw real-time data from SDS
    and routing it to the appropriate UI components and views.
    """

    def __init__(self, page: ft.Page, dashboard_view, security_ui, settings_view, locale_manager):
        self.page = page
        self.dashboard_view = dashboard_view
        self.security_ui = security_ui
        self.settings_view = settings_view
        self.locale_manager = locale_manager

    def handle_sds_data(self, data: dict):
        msg_type = data.get("type")
        if msg_type == "auth_response":
            self.security_ui.handle_auth_response(data.get("payload", {}))
        elif msg_type == "lockdown_event":
            if data.get("payload", {}).get("active", False):
                self.security_ui.trigger_lockdown()
        elif msg_type == "users_list":
            if hasattr(self.settings_view, "account_card") and self.settings_view.account_card:
                self.settings_view.account_card.update_user_list(data.get("payload", {}).get("users", []))
        elif msg_type == "account_response":
            payload = data.get("payload", {})
            action_type = payload.get("action", "")
            success = payload.get("success", False)
            if success:
                msg = self.locale_manager.get_string(
                    "accounts.success_action", "Action ({action_type}) completed successfully!"
                ).replace("{action_type}", action_type)
            else:
                msg = self.locale_manager.get_string(
                    "accounts.fail_action",
                    "Action ({action_type}) failed. Check credentials or if the user already exists.",
                ).replace("{action_type}", action_type)
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(msg), bgcolor=ft.Colors.GREEN_700 if success else ft.Colors.RED_700
            )
            self.page.snack_bar.open = True
            self.page.update()
        elif msg_type == "hardware_status_update":
            payload = data.get("payload", {})
            if isinstance(payload, dict):
                try:
                    from src.controller.connection_manager import HardwareConnectionManager

                    HardwareConnectionManager.get_instance(
                        locale_manager=self.locale_manager
                    ).update_remote_hardware_status(payload)
                except Exception:
                    pass
                hw_handler = getattr(self.settings_view, "hardware_handler", None)
                if hw_handler is not None and getattr(hw_handler, "page", None) is not None:
                    try:
                        hw_handler.refresh_ui()
                    except Exception:
                        pass
        elif msg_type == "hardware_trap":
            payload = data.get("payload", {})
            if isinstance(payload, dict):
                self.handle_hardware_trap(payload)
        elif msg_type == "evp_telemetry":
            payload = data.get("payload", {})
            if isinstance(payload, dict):
                try:
                    from src.evp.evp_notifier import EVPNotifier

                    EVPNotifier.get_instance().notify(payload)
                except Exception:
                    pass
        elif msg_type == "tailscale_response":
            payload = data.get("payload", {})
            rg_card = getattr(self.settings_view, "remote_gateway_card", None)
            if rg_card is not None and hasattr(rg_card, "handle_remote_response"):
                try:
                    rg_card.handle_remote_response(payload if isinstance(payload, dict) else {})
                except Exception:
                    pass
        else:
            if isinstance(data.get("hardware_status"), dict):
                try:
                    from src.controller.connection_manager import HardwareConnectionManager

                    HardwareConnectionManager.get_instance(
                        locale_manager=self.locale_manager
                    ).update_remote_hardware_status(data["hardware_status"])
                except Exception:
                    pass
            self.dashboard_view.update_live_data(data)
            # Optimization Note: Broadcast to CCO is already performed directly
            # by DashboardOrchestrator at the source, eliminating duplication and UI blocking in Flet.

    def _broadcast_to_cco(self, data: dict):
        """Dispatches live traffic and TLS updates to the CCO web videowall."""
        try:
            from src.sds.cco_broadcast_client import CCOBroadcastClient

            client = getattr(self, "_cco_broadcast_client", None)
            if client is None:
                client = CCOBroadcastClient(timeout=0.15)
                self._cco_broadcast_client = client
            if client.broadcast(data):
                return
        except Exception:
            pass

        try:
            from src.drivers.go_gateway_client import GoGatewayClient

            gw_client = GoGatewayClient.get_instance()
            if gw_client.is_running():
                gw_client.send_command("cco_broadcast", data={"type": "congestion_update", **data})
        except Exception:
            pass

    def handle_hardware_trap(self, event_data: dict):
        """Displays a prominent visual toast notification in Flet when a hardware/software trap arrives."""
        try:
            intersection_id = event_data.get("intersection_id", "DESCONHECIDO")
            level = event_data.get("level", "CRITICAL")
            details = (
                event_data.get("details")
                or event_data.get("message")
                or event_data.get("raw_message")
                or "Alerta do controlador"
            )

            if details.startswith("[") and "]" in details:
                clean_display = str(details)
            elif intersection_id and intersection_id != "DESCONHECIDO":
                clean_display = f"[Cruzamento {intersection_id}] {details}"
            else:
                clean_display = str(details)

            bg = ft.Colors.RED_800 if str(level).upper() == "CRITICAL" else ft.Colors.ORANGE_800

            self.page.snack_bar = ft.SnackBar(
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=ft.Colors.WHITE, size=24),
                        ft.Text(clean_display, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                    ],
                    spacing=10,
                ),
                bgcolor=bg,
                duration=5000,
            )
            self.page.snack_bar.open = True
            self.page.update()
        except Exception as e:
            pass
