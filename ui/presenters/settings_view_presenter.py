# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Settings View Presenter (UI / Presentation / SOLID: SRP).
Encapsulates form validation, save execution, change discarding, and defaults restoration.
"""

from typing import Any, Callable, List, Optional
import flet as ft

from ui.handlers.settings_change_detector import SettingsChangeDetector


class SettingsViewPresenter:
    """Presenter coordinating business actions and validation for SettingsView."""

    @staticmethod
    def load_initial_settings(all_cards: list, settings: dict, page: Optional[ft.Page] = None) -> None:
        for card in all_cards:
            if hasattr(card, "set_values"):
                card.set_values(settings)
        if page:
            page.update()

    @staticmethod
    def validate_all_fields(all_cards: list) -> bool:
        validation_failed = False
        for card in all_cards:
            if hasattr(card, "validate_fields"):
                if not card.validate_fields():
                    validation_failed = True
                    if hasattr(card, "update") and hasattr(card, "page") and card.page:
                        card.update()
        return not validation_failed

    @staticmethod
    def has_unsaved_changes(
        all_cards: list,
        hardware_handler: Any,
        settings_handler: Any,
        evp_handler: Any,
    ) -> bool:
        return SettingsChangeDetector.has_unsaved_changes(
            all_cards=all_cards,
            hardware_handler=hardware_handler,
            settings_handler=settings_handler,
            evp_handler=evp_handler,
        )

    @classmethod
    def discard_changes(
        cls,
        all_cards: list,
        subsystem_handlers: List[tuple],
        settings_handler: Any,
        page: Optional[ft.Page] = None,
    ) -> None:
        saved_settings = settings_handler.get_current_settings()
        cls.load_initial_settings(all_cards, saved_settings, page)
        for card in all_cards:
            if hasattr(card, "discard_changes") and callable(card.discard_changes):
                card.discard_changes()

        for handler, _ in subsystem_handlers:
            if hasattr(handler, "discard_changes") and callable(handler.discard_changes):
                handler.discard_changes()

        if page:
            is_dark = saved_settings.get("theme_dark", True)
            if isinstance(is_dark, str):
                is_dark = is_dark.lower() in ("true", "1", "yes")
            page.theme_mode = ft.ThemeMode.DARK if is_dark else ft.ThemeMode.LIGHT
            page.update()

    @staticmethod
    def execute_save(
        all_cards: list,
        subsystem_handlers: List[tuple],
        settings_handler: Any,
        settings_client: Any,
        locale_manager: Any,
        dialog_manager: Any,
        page: Optional[ft.Page] = None,
        on_success: Optional[Callable] = None,
    ) -> None:
        if not page or not settings_client:
            return

        new_settings_values = {}
        for card in all_cards:
            if hasattr(card, "get_values"):
                new_settings_values.update(card.get_values())

        payload_to_send = settings_handler.prepare_settings_for_save(new_settings_values)
        settings_client.save_settings(payload_to_send)

        for card in all_cards:
            if hasattr(card, "save_changes") and callable(card.save_changes):
                card.save_changes()

        for handler, _ in subsystem_handlers:
            if hasattr(handler, "save_changes") and callable(handler.save_changes):
                handler.save_changes()

        if "theme_dark" in new_settings_values:
            is_dark = new_settings_values.get("theme_dark", True)
            if isinstance(is_dark, str):
                is_dark = is_dark.lower() in ("true", "1", "yes")
            page.theme_mode = ft.ThemeMode.DARK if is_dark else ft.ThemeMode.LIGHT

        info_title = locale_manager.get_string("settings_view.title")
        info_content = locale_manager.get_string(
            "settings_view.settings_saved_restart",
            default="As configurações foram salvas. Por favor, reinicie a aplicação para que todas as alterações tenham efeito.",
        )

        if dialog_manager:
            dialog_manager.show_info(title=info_title, content=info_content)
        if on_success:
            on_success()
        page.update()

    @staticmethod
    def save_silently(
        all_cards: list,
        subsystem_handlers: List[tuple],
        settings_handler: Any,
        settings_client: Any,
    ) -> None:
        if not settings_client:
            return
        new_settings_values = {}
        for card in all_cards:
            if hasattr(card, "get_values"):
                new_settings_values.update(card.get_values())
        payload_to_send = settings_handler.prepare_settings_for_save(new_settings_values)
        settings_client.save_settings(payload_to_send)

        for card in all_cards:
            if hasattr(card, "save_changes") and callable(card.save_changes):
                card.save_changes()

        for handler, _ in subsystem_handlers:
            if hasattr(handler, "save_changes") and callable(handler.save_changes):
                handler.save_changes()

    @classmethod
    def restore_defaults(
        cls,
        all_cards: list,
        settings_handler: Any,
        locale_manager: Any,
        page: Optional[ft.Page] = None,
    ) -> None:
        if not page:
            return
        default_settings = settings_handler.get_default_settings()
        cls.load_initial_settings(all_cards, default_settings, page)
        msg = locale_manager.get_string(
            "settings_view.settings_restored_default",
            default="Configurações restauradas para os valores padrão!",
        )
        page.snack_bar = ft.SnackBar(content=ft.Text(msg))
        page.snack_bar.open = True
        page.update()
