# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

class AccountSettingsHandler:
    """
    SRP: Manages all Authentication and Accounts business logic, delegating
    actions to the real-time data provider.
    """

    def __init__(self, settings_client):
        self.settings_client = settings_client

    def on_add_user(self, username, password, role):
        if self.settings_client and self.settings_client.live_data_provider:
            self.settings_client.live_data_provider.send_command_to_backend(
                {"type": "add_user", "payload": {"username": username, "password": password, "role": role}}
            )

    def on_remove_user(self, username):
        if self.settings_client and self.settings_client.live_data_provider:
            self.settings_client.live_data_provider.send_command_to_backend(
                {"type": "remove_user", "payload": {"username": username}}
            )

    def on_request_users_list(self):
        if self.settings_client and self.settings_client.live_data_provider:
            self.settings_client.live_data_provider.send_command_to_backend({"type": "list_users"})
