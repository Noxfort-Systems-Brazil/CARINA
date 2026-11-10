# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Defines the MonitorSettingsCard, a component widget for the Settings screen
used to configure integration with the external "Monitor" system via MQTT.
"""

import json
import threading
from typing import Any, Dict, Optional

import flet as ft
import paho.mqtt.client as mqtt

from ui.handlers.locale_manager import LocaleManager


class MonitorSettingsCard(ft.Card):
    """
    A Card encapsulating External Monitor integration settings.
    """

    def __init__(
        self,
        initial_values: Dict[str, Any],
        on_toggle_connection=None,
        locale_manager: Optional[LocaleManager] = None,
    ):
        """
        Initializes the Card with the provided values.
        """
        super().__init__()

        self.on_toggle_connection = on_toggle_connection
        self.lm = locale_manager

        # --- Controls ---
        self.title_text = ft.Text(size=18, weight=ft.FontWeight.BOLD)

        self.is_connected = str(initial_values.get("monitor_enabled", "False")).lower() == "true"

        self.tf_host = ft.TextField(
            value=initial_values.get("monitor_mqtt_host", "localhost"),
            expand=True,
            disabled=self.is_connected,
        )

        # Action Buttons
        self.btn_connect = ft.ElevatedButton(
            icon=ft.Icons.LOGIN_ROUNDED, on_click=self._handle_connect, visible=not self.is_connected
        )

        self.btn_disconnect = ft.OutlinedButton(
            icon=ft.Icons.LOGOUT_ROUNDED, on_click=self._handle_disconnect, visible=self.is_connected
        )

        # Status Display
        self.status_icon = ft.Icon(
            name=ft.Icons.RADIO_BUTTON_CHECKED if self.is_connected else ft.Icons.RADIO_BUTTON_UNCHECKED,
            color=ft.colors.GREEN_500 if self.is_connected else ft.colors.RED_500,
            size=16,
        )
        self.status_text = ft.Text(
            weight=ft.FontWeight.W_500,
        )
        self.status_display = ft.Row([self.status_icon, self.status_text], alignment=ft.MainAxisAlignment.START)

        # --- Card Structure ---
        self.content = ft.Container(
            padding=15,
            content=ft.Column(
                [
                    ft.Row(
                        [ft.Row([ft.Icon(ft.Icons.MONITOR_HEART), self.title_text]), self.status_display],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Divider(),
                    ft.Container(height=5),
                    ft.Row([self.tf_host], alignment=ft.MainAxisAlignment.START),
                    ft.Row([self.btn_connect, self.btn_disconnect], alignment=ft.MainAxisAlignment.END),
                ]
            ),
        )

        if self.lm:
            self.update_translations(self.lm)
        else:
            try:
                from ui.handlers.locale_manager import LocaleManager

                self.update_translations(LocaleManager())
            except Exception:
                pass

    def _update_ui_state(self):
        self.tf_host.disabled = self.is_connected

        self.btn_connect.visible = not self.is_connected
        self.btn_disconnect.visible = self.is_connected

        self.status_icon.name = ft.Icons.RADIO_BUTTON_CHECKED if self.is_connected else ft.Icons.RADIO_BUTTON_UNCHECKED
        self.status_icon.color = ft.colors.GREEN_500 if self.is_connected else ft.colors.RED_500

        status_str = "CONNECTED" if self.is_connected else "DISCONNECTED"
        if hasattr(self, "lm") and self.lm:
            key = (
                "settings_view.monitor_card.status_connected"
                if self.is_connected
                else "settings_view.monitor_card.status_disconnected"
            )
            status_str = self.lm.get_string(key, default=status_str)

        self.status_text.value = status_str.upper()
        self.status_text.color = ft.colors.GREEN_500 if self.is_connected else ft.colors.RED_500

        if self.page:
            self.update()

    def _handle_connect(self, e):
        self.is_connected = True
        self._update_ui_state()

        # Fire an immediate heartbeat in the background so the UI doesn't freeze
        host = self.tf_host.value
        threading.Thread(target=self._send_immediate_ping, args=(host,), daemon=True).start()

        if self.on_toggle_connection:
            self.on_toggle_connection(True, host)

    def _send_immediate_ping(self, host: str):
        """Sends heartbeat in the exact requested format upon UI connection."""
        payload = {"origin": "Carina", "level": "info", "message": "heartbeat"}
        try:
            from src.communication.monitor_transport import is_http_endpoint, normalize_http_url

            if is_http_endpoint(host):
                import requests

                url = normalize_http_url(host)
                requests.post(url, json=payload, timeout=3.0)
            else:
                from src.communication.monitor_transport import MonitorMqttTransport
                target_host, target_port = MonitorMqttTransport.parse_host_port(host, default_port=1883)

                client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="carina_ui_ping")
                client.connect(target_host, target_port, keepalive=5)
                info = client.publish("noxfort/telemetry/", json.dumps(payload), qos=0)
                info.wait_for_publish()
                client.disconnect()
        except Exception as err:
            print(f"Failed to send immediate monitor ping from UI to {host}: {err}")

    def _handle_disconnect(self, e):
        self.is_connected = False
        self._update_ui_state()

        if self.on_toggle_connection:
            self.on_toggle_connection(False, self.tf_host.value)

    def get_values(self) -> Dict[str, Any]:
        """
        Returns a dictionary with current control values in this card.
        """
        return {"monitor_enabled": str(self.is_connected), "monitor_mqtt_host": self.tf_host.value}

    def set_values(self, values: Dict[str, Any]):
        """
        Updates control values in this card based on the provided dictionary.
        """
        self.is_connected = str(values.get("monitor_enabled", "False")).lower() == "true"
        self.tf_host.value = values.get("monitor_mqtt_host", "localhost")
        self._update_ui_state()

    def update_translations(self, lm: LocaleManager):
        """Updates texts in this card based on the LocaleManager."""
        self.lm = lm
        self.title_text.value = lm.get_string(
            "settings_view.monitor_card.title", default="External Monitor Integration"
        )
        self.tf_host.label = lm.get_string(
            "settings_view.monitor_card.host", default="Monitor Host / URL (Ngrok, Cloud, IP ou Broker MQTT)"
        )

        self.btn_connect.text = lm.get_string("settings_view.monitor_card.btn_connect", default="Connect")
        self.btn_disconnect.text = lm.get_string("settings_view.monitor_card.btn_disconnect", default="Disconnect")

        self._update_ui_state()
