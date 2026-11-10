# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Informational UI banner displaying physical episode sizing and street network topology metrics.
"""

from typing import Optional
import flet as ft

from ui.handlers.locale_manager import LocaleManager


class PilotingSchoolPacingBanner:
    """Component managing the informative container and localized metrics display for episode pacing."""

    def __init__(self):
        self.lbl_pacing_info_title = ft.Text(size=13, weight=ft.FontWeight.W_600)
        self.lbl_steps_per_episode = ft.Text(size=12)
        self.lbl_inviolable_floor = ft.Text(size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY)
        self.lbl_topology_summary = ft.Text(size=11, color=ft.Colors.OUTLINE)

        self.container = ft.Container(
            bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.PRIMARY),
            border=ft.border.all(1, ft.Colors.with_opacity(0.3, ft.Colors.PRIMARY)),
            border_radius=8,
            padding=12,
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.TIMER_OUTLINED, size=18, color=ft.Colors.PRIMARY),
                            self.lbl_pacing_info_title,
                        ],
                        spacing=8,
                    ),
                    self.lbl_steps_per_episode,
                    self.lbl_inviolable_floor,
                    self.lbl_topology_summary,
                ],
                spacing=4,
            ),
        )

    def update_labels(
        self,
        steps: int,
        duration: float,
        min_episodes: int,
        signals: int,
        connections: int,
        complexity: float,
        lm: Optional[LocaleManager] = None,
    ):
        """Updates text descriptions with localized formatting and dynamic values."""
        comp = f"{complexity:.2f}"
        if lm:
            self.lbl_pacing_info_title.value = lm.get_string(
                "settings_view.piloting_school_card.pacing_info_title",
                default="Dimensionamento Físico de Episódio (Topologia Viária)",
            )
            self.lbl_steps_per_episode.value = lm.get_string(
                "settings_view.piloting_school_card.steps_per_episode",
                default=f"1 episódio = {steps} passos ({duration:.1f}s @ 250ms)",
                steps=steps,
                duration=f"{duration:.1f}",
            )
            self.lbl_inviolable_floor.value = lm.get_string(
                "settings_view.piloting_school_card.inviolable_week_floor",
                default=f"Piso inviolável de segurança: {min_episodes} episódios (1 semana completa / 168h)",
                min_episodes=min_episodes,
            )
            self.lbl_topology_summary.value = lm.get_string(
                "settings_view.piloting_school_card.network_topology_summary",
                default=f"Malha: {signals} semáforos, {connections} vias unificadas, Complexidade C_topo = {comp}",
                signals=signals,
                connections=connections,
                complexity=comp,
            )
        else:
            self.lbl_pacing_info_title.value = "Dimensionamento Físico de Episódio (Topologia Viária)"
            self.lbl_steps_per_episode.value = f"1 episódio = {steps} passos ({duration:.1f}s @ 250ms)"
            self.lbl_inviolable_floor.value = f"Piso inviolável de segurança: {min_episodes} episódios (1 semana completa / 168h)"
            self.lbl_topology_summary.value = f"Malha: {signals} semáforos, {connections} vias unificadas, Complexidade C_topo = {comp}"
