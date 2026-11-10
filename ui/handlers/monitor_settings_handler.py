# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

class MonitorSettingsHandler:
    """
    SRP: Manages all business logic related to the connection with the external Monitor system.
    """

    def __init__(self, settings_client):
        self.settings_client = settings_client

    def on_monitor_toggle(self, enabled: bool, host: str):
        # Synchronize local UI-process MonitorClient if any was initialized
        try:
            from src.communication.monitor_client import MonitorClient

            if MonitorClient._instance:
                if enabled:
                    MonitorClient._instance.connect_manual(host)
                else:
                    MonitorClient._instance.disconnect_manual()
        except Exception:
            pass

        if self.settings_client and self.settings_client.live_data_provider:
            command = {"type": "set_monitor_connection", "payload": {"enabled": enabled, "host": host}}
            self.settings_client.live_data_provider.send_command_to_backend(command)
