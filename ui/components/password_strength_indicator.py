# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Any, Dict, Tuple
import flet as ft

from ui.handlers.locale_manager import LocaleManager

from src.security.password_policy import PasswordValidator


class PasswordStrengthIndicator(ft.Container):
    """Component responsible solely for rendering and updating password strength and criteria badges."""

    def __init__(self, locale_manager: LocaleManager):
        super().__init__(padding=ft.padding.only(left=2, right=2, top=0, bottom=6))
        self.locale_manager = locale_manager

        self.strength_title = ft.Text(
            self.locale_manager.get_string("accounts.password_strength", "Força da Senha:"),
            size=12,
            weight=ft.FontWeight.W_500,
        )
        self.strength_status = ft.Text(
            self.locale_manager.get_string("accounts.strength_none", "Não informada"),
            size=12,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.GREY_500,
        )
        self.strength_bar = ft.ProgressBar(
            value=0.0,
            color=ft.Colors.GREY_600,
            bgcolor=ft.Colors.GREY_800,
            height=6,
        )

        # Requirement Badges
        self.crit_length_icon, self.crit_length_text, self.badge_length = self._create_badge(
            self.locale_manager.get_string("accounts.req_length", "8+ caracteres")
        )
        self.crit_upper_icon, self.crit_upper_text, self.badge_upper = self._create_badge(
            self.locale_manager.get_string("accounts.req_upper", "Maiúscula (A-Z)")
        )
        self.crit_num_icon, self.crit_num_text, self.badge_numbers = self._create_badge(
            self.locale_manager.get_string("accounts.req_numbers", "Números (0-9)")
        )
        self.crit_spec_icon, self.crit_spec_text, self.badge_special = self._create_badge(
            self.locale_manager.get_string("accounts.req_special", "Especial (!@#$...)")
        )
        self.crit_lower_icon, self.crit_lower_text, self.badge_lower = self._create_badge(
            self.locale_manager.get_string("accounts.req_lower", "Minúscula (a-z)")
        )

        self.content = ft.Column(
            [
                ft.Row([self.strength_title, self.strength_status], spacing=6),
                self.strength_bar,
                ft.Row(
                    [
                        self.badge_length,
                        self.badge_upper,
                        self.badge_numbers,
                        self.badge_special,
                        self.badge_lower,
                    ],
                    wrap=True,
                    spacing=12,
                ),
            ],
            spacing=6,
        )

    def _create_badge(self, text: str) -> Tuple[ft.Icon, ft.Text, ft.Row]:
        icon = ft.Icon(ft.Icons.RADIO_BUTTON_UNCHECKED, size=14, color=ft.Colors.GREY_600)
        label = ft.Text(text, size=11, color=ft.Colors.GREY_500)
        row = ft.Row([icon, label], spacing=4, tight=True)
        return icon, label, row

    def _update_badge(self, icon: ft.Icon, label: ft.Text, is_met: bool) -> None:
        if is_met:
            icon.name = ft.Icons.CHECK_CIRCLE_ROUNDED
            icon.color = ft.Colors.GREEN_400
            label.color = ft.Colors.GREEN_200
        else:
            icon.name = ft.Icons.RADIO_BUTTON_UNCHECKED
            icon.color = ft.Colors.GREY_600
            label.color = ft.Colors.GREY_500

    def reset(self) -> None:
        self.strength_status.value = self.locale_manager.get_string("accounts.strength_none", "Não informada")
        self.strength_status.color = ft.Colors.GREY_500
        self.strength_bar.value = 0.0
        self.strength_bar.color = ft.Colors.GREY_600
        self._update_badge(self.crit_length_icon, self.crit_length_text, False)
        self._update_badge(self.crit_upper_icon, self.crit_upper_text, False)
        self._update_badge(self.crit_num_icon, self.crit_num_text, False)
        self._update_badge(self.crit_spec_icon, self.crit_spec_text, False)
        self._update_badge(self.crit_lower_icon, self.crit_lower_text, False)

    def update_from_password(self, pwd: str) -> Dict[str, Any]:
        strength = PasswordValidator.calculate_strength(pwd)
        criteria = strength["criteria"]

        self._update_badge(self.crit_length_icon, self.crit_length_text, criteria["length"])
        self._update_badge(self.crit_upper_icon, self.crit_upper_text, criteria["uppercase"])
        self._update_badge(self.crit_num_icon, self.crit_num_text, criteria["numbers"])
        self._update_badge(self.crit_spec_icon, self.crit_spec_text, criteria["special"])
        self._update_badge(self.crit_lower_icon, self.crit_lower_text, criteria["lowercase"])

        level = strength["level"]
        self.strength_bar.value = strength["progress"]

        levels_map = {
            "none": (self.locale_manager.get_string("accounts.strength_none", "Não informada"), ft.Colors.GREY_500, ft.Colors.GREY_600),
            "very_weak": (self.locale_manager.get_string("accounts.strength_very_weak", "Muito Fraca"), ft.Colors.RED_400, ft.Colors.RED_500),
            "weak": (self.locale_manager.get_string("accounts.strength_weak", "Fraca"), ft.Colors.ORANGE_400, ft.Colors.ORANGE_500),
            "medium": (self.locale_manager.get_string("accounts.strength_medium", "Média"), ft.Colors.AMBER_400, ft.Colors.AMBER_500),
            "strong": (self.locale_manager.get_string("accounts.strength_strong", "Forte"), ft.Colors.LIGHT_GREEN_400, ft.Colors.LIGHT_GREEN_500),
            "very_strong": (self.locale_manager.get_string("accounts.strength_very_strong", "Muito Forte"), ft.Colors.GREEN_400, ft.Colors.GREEN_600),
        }
        text_val, text_col, bar_col = levels_map.get(level, levels_map["none"])
        self.strength_status.value = text_val
        self.strength_status.color = text_col
        self.strength_bar.color = bar_col

        return strength

    def update_translations(self, lm: LocaleManager) -> None:
        self.locale_manager = lm
        self.strength_title.value = lm.get_string("accounts.password_strength", "Força da Senha:")
        self.crit_length_text.value = lm.get_string("accounts.req_length", "8+ caracteres")
        self.crit_upper_text.value = lm.get_string("accounts.req_upper", "Maiúscula (A-Z)")
        self.crit_num_text.value = lm.get_string("accounts.req_numbers", "Números (0-9)")
        self.crit_spec_text.value = lm.get_string("accounts.req_special", "Especial (!@#$...)")
        self.crit_lower_text.value = lm.get_string("accounts.req_lower", "Minúscula (a-z)")
