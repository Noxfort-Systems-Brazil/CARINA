# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Callable, List, Optional
import flet as ft

from ui.clients.settings_client import SettingsClient
from ui.dialogs.confirmation_dialog_manager import ConfirmationDialogManager
from ui.handlers.locale_manager import LocaleManager
from ui.handlers.settings_handler import SettingsHandler
from ui.presenters.settings_view_presenter import SettingsViewPresenter


class SettingsView(ft.Container):
    """
    Settings Modal View component.
    Declarative container delegating business actions, validation,
    and save coordination to SettingsViewPresenter (MVP / Clean Architecture).
    """

    def __init__(
        self,
        locale_manager: LocaleManager,
        settings_client: SettingsClient,
        tab_definitions: list,
        warning_text_ref: ft.Text,
        handler: Optional[SettingsHandler] = None,
    ):
        super().__init__(expand=True, padding=10)

        self.locale_manager = locale_manager
        self.settings_client = settings_client
        self.tab_definitions = tab_definitions
        self.warning_text = warning_text_ref

        self.handler = handler or SettingsHandler()
        self.dialog_manager: ConfirmationDialogManager | None = None
        self._is_saving: bool = False

        # Injected properties
        self.hardware_handler = None
        self.hardware_card = None
        self.evp_handler = None
        self.evp_card = None
        self.account_card = None

        # Gather all cards for polymorphic operations
        self.all_cards = []
        tab_controls = []
        for tab in self.tab_definitions:
            tab_column = ft.Column(controls=tab["cards"], spacing=15, scroll=ft.ScrollMode.ADAPTIVE)
            tab_controls.append(ft.Tab(content=tab_column, text="", icon=tab["icon"]))
            for item in tab["cards"]:
                if isinstance(item, ft.Card):
                    self.all_cards.append(item)

        self.tabs = ft.Tabs(selected_index=0, animation_duration=300, expand=True, tabs=tab_controls)

        self.title_text = ft.Text(size=24, weight=ft.FontWeight.BOLD)
        self.save_button = ft.ElevatedButton(icon=ft.Icons.SAVE_ROUNDED, on_click=self._save_click)
        self.restore_button = ft.TextButton(icon=ft.Icons.SETTINGS_BACKUP_RESTORE, on_click=self._restore_click)

        self.content = ft.Column(
            controls=[
                ft.Row([ft.Icon(ft.Icons.SETTINGS), self.title_text]),
                self.tabs,
                ft.Row([self.restore_button, self.save_button], alignment=ft.MainAxisAlignment.END, spacing=20),
            ],
            expand=True,
            spacing=15,
        )

    @property
    def subsystem_handlers(self) -> List[tuple]:
        handlers = []
        if self.hardware_handler:
            handlers.append((self.hardware_handler, self.hardware_card))
        if self.evp_handler:
            handlers.append((self.evp_handler, self.evp_card))
        return handlers

    def did_mount(self):
        if self.page:
            self.dialog_manager = ConfirmationDialogManager(self.page, self.locale_manager)
            for handler, card in self.subsystem_handlers:
                if card and hasattr(handler, "mount") and callable(handler.mount):
                    handler.mount(self.page, card)

            for card in self.all_cards:
                if hasattr(card, "mount") and callable(card.mount):
                    card.mount(self.page)
                if hasattr(card, "logo_file_picker") and card.logo_file_picker not in self.page.overlay:
                    self.page.overlay.append(card.logo_file_picker)

        self.update_translations(self.locale_manager)

    def update_translations(self, lm: LocaleManager):
        self.title_text.value = lm.get_string("settings_view.title")
        self.save_button.text = lm.get_string("settings_view.save_button")
        self.restore_button.text = lm.get_string("settings_view.restore_button")
        self.warning_text.value = lm.get_string("settings_view.warning_text")

        for idx, tab_spec in enumerate(self.tab_definitions):
            tab_text = lm.get_string(tab_spec["title_key"], tab_spec["default_title"])
            if tab_spec.get("is_dynamic_fallback"):
                self.tabs.tabs[idx].text = tab_text if tab_text and "!" not in tab_text else tab_spec["default_title"]
            else:
                self.tabs.tabs[idx].text = tab_text

        for card in self.all_cards:
            if hasattr(card, "update_translations"):
                card.update_translations(lm)

        if self.dialog_manager:
            self.dialog_manager.update_translations()

        if self.page:
            self.update()

    def _load_initial_settings(self, settings: dict = None):
        if settings is None:
            settings = self.handler.get_current_settings()
        SettingsViewPresenter.load_initial_settings(self.all_cards, settings, self.page)

    def validate_all_fields(self) -> bool:
        return SettingsViewPresenter.validate_all_fields(self.all_cards)

    def has_unsaved_changes(self) -> bool:
        return SettingsViewPresenter.has_unsaved_changes(
            all_cards=self.all_cards,
            hardware_handler=self.hardware_handler,
            settings_handler=self.handler,
            evp_handler=self.evp_handler,
        )

    def save_and_close(self, on_close: Optional[Callable] = None):
        if not self.validate_all_fields():
            info_title = self.locale_manager.get_string("settings_view.title")
            info_content = self.locale_manager.get_string(
                "settings_view.validation_error_message",
                default="Erro de validação: Por favor, corrija os erros nos campos destacados antes de salvar.",
            )
            if self.dialog_manager:
                self.dialog_manager.show_info(title=info_title, content=info_content)
            return

        self._is_saving = True
        try:
            self._execute_save(on_success=on_close)
        finally:
            self._is_saving = False

    def _save_click(self, e):
        if not self.dialog_manager:
            return

        if not self.validate_all_fields():
            info_title = self.locale_manager.get_string("settings_view.title")
            info_content = self.locale_manager.get_string(
                "settings_view.validation_error_message",
                default="Erro de validação: Por favor, corrija os erros nos campos destacados antes de salvar.",
            )
            self.dialog_manager.show_info(title=info_title, content=info_content)
            return

        self._is_saving = True

        def _on_confirm():
            try:
                self._execute_save()
            finally:
                self._is_saving = False

        def _on_cancel():
            self._is_saving = False

        title = self.locale_manager.get_string("dialogs.confirm_action_title")
        content = self.locale_manager.get_string("dialogs.save_settings_content")
        self.dialog_manager.show(
            title=title, content=content, on_confirm=_on_confirm, on_cancel=_on_cancel
        )

    def discard_changes(self):
        if getattr(self, "_is_saving", False):
            return
        SettingsViewPresenter.discard_changes(
            self.all_cards, self.subsystem_handlers, self.handler, self.page
        )

    def _execute_save(self, on_success: Optional[Callable] = None):
        SettingsViewPresenter.execute_save(
            all_cards=self.all_cards,
            subsystem_handlers=self.subsystem_handlers,
            settings_handler=self.handler,
            settings_client=self.settings_client,
            locale_manager=self.locale_manager,
            dialog_manager=self.dialog_manager,
            page=self.page,
            on_success=on_success,
        )

    def save_silently(self):
        SettingsViewPresenter.save_silently(
            all_cards=self.all_cards,
            subsystem_handlers=self.subsystem_handlers,
            settings_handler=self.handler,
            settings_client=self.settings_client,
        )

    def _restore_click(self, e):
        SettingsViewPresenter.restore_defaults(
            all_cards=self.all_cards,
            settings_handler=self.handler,
            locale_manager=self.locale_manager,
            page=self.page,
        )
