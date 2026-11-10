# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Defines the SettingsClient, responsible for communicating UI configuration
changes to the backend.
"""

import logging
from typing import TYPE_CHECKING, Any, Dict

# Prevents circular import, allowing type annotation
if TYPE_CHECKING:
    from ui.providers.live_data_provider import LiveDataProvider


class SettingsClient:
    """
    Sends configuration update commands to the backend via
    the real-time data provider (WebSocket).
    """

    def __init__(self, live_data_provider: "LiveDataProvider"):
        """
        Initializes the settings client.

        Args:
            live_data_provider: The LiveDataProvider instance that manages the
                                WebSocket connection with the backend.
        """
        self.live_data_provider = live_data_provider
        logging.info("[SettingsClient] Cliente de configurações inicializado.")

    def save_settings(self, settings_payload: Dict[str, Any]):
        """
        Creates a standardized command and sends it to the backend to save
        the new settings.

        Args:
            settings_payload (Dict[str, Any]): A dictionary containing the
                                               settings to be saved.
        """
        if not self.live_data_provider:
            logging.error("[SettingsClient] LiveDataProvider não foi fornecido. Impossível enviar configurações.")
            return

        command = {"type": "save_settings", "payload": settings_payload}

        self.live_data_provider.send_command_to_backend(command)
        logging.info(
            f"[SettingsClient] Comando 'save_settings' enviado para o backend com {len(settings_payload)} chaves."
        )

    def send_command(self, cmd_type: str, payload: Dict[str, Any]):
        """
        Sends a generic command to the backend.

        Args:
            cmd_type (str): The command type (e.g. 'set_hardware_connection').
            payload (Dict[str, Any]): The data associated with the command.
        """
        if not self.live_data_provider:
            logging.error(
                f"[SettingsClient] LiveDataProvider não foi fornecido. Impossível enviar comando '{cmd_type}'."
            )
            return

        command = {"type": cmd_type, "payload": payload}

        self.live_data_provider.send_command_to_backend(command)
        logging.info(f"[SettingsClient] Comando '{cmd_type}' enviado para o backend.")
