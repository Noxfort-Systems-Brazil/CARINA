# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Defines the Control Panel widget.
"""

from typing import Callable, Dict

import flet as ft

from ui.clients.control_client import ControlClient
from ui.handlers.locale_manager import LocaleManager

# --- CHANGE APPLIED HERE: Using absolute imports from 'ui' ---
from ui.widgets.global_controls_widget import GlobalControlsWidget
from ui.widgets.specific_controls_widget import SpecificControlsWidget
from ui.widgets.street_info_widget import StreetInfoWidget

# --- END OF CHANGE ---


class ControlPanelWidget(ft.Container):
    """
    Widget that organizes the global and specific control panels.
    """

    def __init__(
        self,
        control_client: ControlClient,
        locale_manager: LocaleManager,
        security_ui=None,
        on_specific_command: Callable[[str, str], None] = None,
        on_street_override: Callable[[str, str], None] = None,
        on_details_close: Callable[[], None] = None,
        on_mode_change: Callable[[str], None] = None,
    ):
        super().__init__(width=300, bgcolor=ft.Colors.BLUE_GREY_900, border_radius=10, padding=15)

        self.on_details_close = on_details_close

        self.on_street_override = on_street_override

        self.global_controls = GlobalControlsWidget(
            control_client=control_client, locale_manager=locale_manager, on_mode_change=on_mode_change
        )

        self.specific_controls = SpecificControlsWidget(
            control_client=control_client,
            locale_manager=locale_manager,
            security_ui=security_ui,
            on_close=self.ocultar_todos_detalhes,
            on_specific_command=on_specific_command,
        )

        self.street_info = StreetInfoWidget(
            locale_manager=locale_manager,
            control_client=control_client,
            security_ui=security_ui,
            on_close=self.ocultar_todos_detalhes,
            on_street_override=self._handle_street_override,
        )

        self.content = ft.Column(
            controls=[self.global_controls, self.specific_controls, self.street_info],
            spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

    def update_translations(self, lm: LocaleManager):
        """Commands child widgets to update to the new locale."""
        self.global_controls.update_translations(lm)
        self.specific_controls.update_translations(lm)
        self.street_info.update_translations(lm)
        if self.page:
            self.update()

    def exibir_controles_semaforo(self, semaphore_id: str, semaphore_data: Dict, phase: str, mode: str):
        self.street_info.visible = False
        self.specific_controls.exibir_controles_semaforo(semaphore_id, semaphore_data, phase, mode)
        if self.page:
            self.update()

    def _handle_street_override(self, street_id: str, state: str):
        if self.on_street_override:
            self.on_street_override(street_id, state)

    def exibir_info_rua(self, street_id: str, street_data: dict):
        self.specific_controls.visible = False
        self.street_info.update_and_show(street_id, street_data)
        if self.page:
            self.update()

    def ocultar_todos_detalhes(self, e=None):
        self.specific_controls.visible = False
        self.street_info.visible = False
        if self.on_details_close:
            self.on_details_close()
        if self.page:
            self.update()
