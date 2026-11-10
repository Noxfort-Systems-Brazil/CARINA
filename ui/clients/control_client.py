# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Defines the ControlClient.

This version connects to the LiveDataProvider, creating
a 'feedback loop' that allows UI commands (such as timing changes)
to affect mock simulation data in real time.
"""

import logging
from typing import TYPE_CHECKING

# We use TYPE_CHECKING to avoid circular import, a good practice
if TYPE_CHECKING:
    from ui.providers.live_data_provider import LiveDataProvider


class ControlClient:
    """
    Translates UI actions into commands and sends them to the backend.
    """

    def __init__(self, live_data_provider: "LiveDataProvider" = None):
        """
        Initializes the control client.

        Args:
            live_data_provider: An optional reference to the data provider
                                for UI feedback loop.
        """
        self.live_data_provider = live_data_provider
        logging.info("[ControlClient] Cliente de comando inicializado.")

    def set_global_mode(self, mode: str):
        """
        Sends a command to change the global system operation mode.
        """
        logging.info(f"--- [CONTROL_CLIENT] ---> COMANDO ENVIADO: Mudar modo global para '{mode.upper()}'")
        if self.live_data_provider:
            command = {"type": "set_global_mode", "payload": {"mode": mode}}
            self.live_data_provider.send_command_to_backend(command)

    def set_semaphore_override(self, semaphore_id: str, state: str):
        """
        Sends a command to apply an override to a specific traffic light.
        """
        logging.info(
            f"--- [CONTROL_CLIENT] ---> COMANDO ENVIADO: Aplicar override no semáforo '{semaphore_id}' para o estado '{state.upper()}'"
        )
        if self.live_data_provider:
            command = {"type": "set_semaphore_override", "payload": {"semaphore_id": semaphore_id, "state": state}}
            self.live_data_provider.send_command_to_backend(command)

    def set_street_override(self, street_id: str, state: str):
        """
        Sends a command to block or unblock a street.
        """
        logging.info(
            f"--- [CONTROL_CLIENT] ---> COMANDO ENVIADO: Aplicar override na rua '{street_id}' para o estado '{state.upper()}'"
        )
        if self.live_data_provider:
            command = {"type": "set_street_override", "payload": {"street_id": street_id, "state": state}}
            self.live_data_provider.send_command_to_backend(command)

    def trigger_analysis(self):
        """
        Sends a command to trigger planning analysis immediately.
        """
        logging.info("--- [CONTROL_CLIENT] ---> COMANDO ENVIADO: Disparar análise de planejamento")
        if self.live_data_provider:
            command = {"type": "trigger_analysis", "payload": {}}
            self.live_data_provider.send_command_to_backend(command)

    def trigger_mfd_analysis(self):
        """
        Sends a command to trigger MFD optimization analysis immediately.
        """
        logging.info("--- [CONTROL_CLIENT] ---> COMANDO ENVIADO: Disparar análise MFD")
        if self.live_data_provider:
            command = {"type": "trigger_mfd_analysis", "payload": {}}
            self.live_data_provider.send_command_to_backend(command)

    def toggle_semaphore_yellow_schedule(self, semaphore_id: str):
        """
        Sends a command to toggle inclusion of a traffic light in the flashing yellow schedule.
        """
        logging.info(f"--- [CONTROL_CLIENT] ---> COMANDO ENVIADO: Alternar agendamento de amarelo para {semaphore_id}")
        if self.live_data_provider:
            command = {"type": "toggle_yellow_schedule_semaphore", "payload": {"semaphore_id": semaphore_id}}
            self.live_data_provider.send_command_to_backend(command)

    def set_yellow_schedule(self, schedule_payload: dict):
        """
        Sends a command to update flashing yellow schedule settings.
        """
        logging.info("--- [CONTROL_CLIENT] ---> COMANDO ENVIADO: Atualizar agendamento de amarelo intermitente")
        if self.live_data_provider:
            command = {"type": "set_yellow_schedule", "payload": schedule_payload}
            self.live_data_provider.send_command_to_backend(command)

