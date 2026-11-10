# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Defines the TrafficLightWidget class.

This is the simplified final version. It is a dumb component whose sole
responsibility is to visually display a light state commanded
by an external controller. The click logic has been removed to be
centralized in the parent widget.
"""

import logging
from typing import Callable

import flet as ft


class TrafficLightWidget(ft.Container):
    """
    A visual widget representing a traffic light.
    """

    def __init__(self, semaphore_id: str, initial_state: str = "RED"):
        super().__init__()

        self.semaphore_id = semaphore_id
        self.current_state = initial_state

        self.width = 20
        self.height = 50
        self.bgcolor = ft.Colors.BLACK
        self.border_radius = 5
        self.padding = 4

        self.lights = {
            "RED": self._criar_luz(ft.Colors.RED),
            "YELLOW": self._criar_luz(ft.Colors.AMBER),
            "GREEN": self._criar_luz(ft.Colors.GREEN),
        }

        self.content = ft.Column(
            controls=list(self.lights.values()),
            spacing=4,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        self._update_visuals()

    def _criar_luz(self, cor: str) -> ft.Container:
        """Creates a single circular container for a light."""
        return ft.Container(
            width=12,
            height=12,
            border_radius=6,
            bgcolor=ft.Colors.with_opacity(0.2, cor),
            animate=ft.Animation(100, "ease"),
        )

    def _update_visuals(self):
        """Updates light colors based on current state."""
        for state, light_container in self.lights.items():
            base_color = getattr(ft.Colors, state)
            light_container.bgcolor = ft.Colors.with_opacity(0.2, base_color)

        # The "OFF" state now simply doesn't turn on any lights
        if self.current_state in self.lights:
            light_to_turn_on = self.lights[self.current_state]
            base_color = getattr(ft.Colors, self.current_state)
            light_to_turn_on.bgcolor = base_color

        if self.page:
            try:
                self.update()
            except Exception:
                pass

    def set_state(self, new_state: str):
        """
        Public method to alter traffic light state.
        """
        valid_states = ["RED", "YELLOW", "GREEN", "ALERT", "OFF"]
        if new_state not in valid_states:
            logging.warning(f"Tentativa de definir estado inválido '{new_state}' para o semáforo {self.semaphore_id}")
            return

        visual_state = "YELLOW" if new_state == "ALERT" else new_state

        if self.current_state != visual_state:
            self.current_state = visual_state
            self._update_visuals()

    def apply_telemetry(self, telemetry_data: dict, overrides: dict, blink_toggle: bool):
        """
        Applies new telemetry data ensuring OCP. The MapAnimator doesn't need to know
        how a traffic light processes its data.
        """
        override_state = overrides.get(self.semaphore_id)
        if override_state:
            if override_state == "ALERT":
                self.set_state("YELLOW" if blink_toggle else "OFF")
            elif override_state == "OFF":
                self.set_state("OFF")
        else:
            semaforo_data = telemetry_data.get(self.semaphore_id, {})
            new_state = semaforo_data.get("display_state", "RED")
            self.set_state(new_state)
