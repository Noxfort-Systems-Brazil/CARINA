# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Callable

import flet as ft

from ..handlers.locale_manager import LocaleManager


class ConfirmationDialogManager:
    """
    Manages the display of confirmation and informative dialogs.
    """

    def __init__(self, page: ft.Page, locale_manager: LocaleManager):
        self.page = page
        self.locale_manager = locale_manager
        self._on_confirm_callback: Callable | None = None
        self._on_cancel_callback: Callable | None = None

        self._confirm_button = ft.ElevatedButton(
            self.locale_manager.get_string("dialogs.confirm_button", default="Confirmar"), on_click=self._handle_confirm
        )
        self._cancel_button = ft.TextButton(
            self.locale_manager.get_string("dialogs.cancel_button", default="Cancelar"), on_click=self._handle_cancel
        )

        # --- CHANGE 1: Add a new "Close" button for informational dialogs ---
        self._close_button = ft.TextButton(
            self.locale_manager.get_string("dialogs.close_button", default="Fechar"), on_click=self._handle_cancel
        )

        self._dialog_title_text = ft.Text(weight=ft.FontWeight.BOLD, size=24)

        self._content_text = ft.Text(size=16)

        self._dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=ft.Colors.AMBER, size=30),
                    self._dialog_title_text,
                ]
            ),
            content=self._content_text,
            actions=[],  # Actions will be defined dynamically
            actions_alignment=ft.MainAxisAlignment.END,
            on_dismiss=self._handle_cancel,
        )

        if self._dialog not in self.page.overlay:
            self.page.overlay.append(self._dialog)

        self.update_translations()

    def update_translations(self):
        self._confirm_button.text = self.locale_manager.get_string("dialogs.confirm_button")
        self._cancel_button.text = self.locale_manager.get_string("dialogs.cancel_button")
        self._close_button.text = self.locale_manager.get_string("dialogs.close_button")

    def show(self, title: str, content: str, on_confirm: Callable, on_cancel: Callable | None = None):
        """
        Displays a confirmation dialog with two buttons (Confirm/Cancel).
        """
        self._on_confirm_callback = on_confirm
        self._on_cancel_callback = on_cancel

        self._dialog_title_text.value = title
        self._content_text.value = content

        # --- CHANGE 2: Define the actions for a confirmation dialog ---
        self._dialog.actions = [self._cancel_button, self._confirm_button]
        self._dialog.actions_alignment = ft.MainAxisAlignment.SPACE_BETWEEN

        self._dialog.open = True
        if self.page:
            self.page.update()

    # --- CHANGE 3: New method for displaying an informational dialog ---
    def show_info(self, title: str, content: str):
        """
        Displays an informative dialog with a single "Close" button.
        """
        self._on_confirm_callback = None  # No confirmation action

        self._dialog_title_text.value = title
        self._content_text.value = content

        # Defines the actions for an informative dialog
        self._dialog.actions = [self._close_button]
        self._dialog.actions_alignment = ft.MainAxisAlignment.END

        self._dialog.open = True
        if self.page:
            self.page.update()

    def show_unsaved_changes(
        self,
        on_save: Callable,
        on_discard: Callable,
        on_cancel: Callable | None = None,
    ):
        """
        Displays a dialog warning about unsaved changes with 3 actions:
        - Cancel (keeps dialog open)
        - Discard (reverts changes and closes)
        - Save & Close (saves changes and closes)
        """
        self._on_confirm_callback = None
        self._dialog_title_text.value = self.locale_manager.get_string(
            "settings_view.unsaved_changes_title", default="Alterações Não Salvas"
        )
        self._content_text.value = self.locale_manager.get_string(
            "settings_view.unsaved_changes_message",
            default="Você possui alterações que não foram salvas. O que deseja fazer?",
        )

        def _handle_cancel_click(e):
            self._close_dialog()
            if on_cancel:
                on_cancel()

        def _handle_discard_click(e):
            self._close_dialog()
            if on_discard:
                on_discard()

        def _handle_save_click(e):
            self._close_dialog()
            if on_save:
                on_save()

        btn_cancel = ft.TextButton(
            self.locale_manager.get_string("settings_view.btn_cancel", default="Cancelar"),
            on_click=_handle_cancel_click,
        )
        btn_discard = ft.OutlinedButton(
            self.locale_manager.get_string("settings_view.btn_discard", default="Descartar"),
            on_click=_handle_discard_click,
        )
        btn_save = ft.ElevatedButton(
            self.locale_manager.get_string("settings_view.btn_save_and_close", default="Salvar e Fechar"),
            icon=ft.Icons.SAVE_ROUNDED,
            on_click=_handle_save_click,
        )

        self._dialog.actions = [btn_cancel, btn_discard, btn_save]
        self._dialog.actions_alignment = ft.MainAxisAlignment.END

        self._dialog.open = True
        if self.page:
            self.page.update()

    def _close_dialog(self):
        self._dialog.open = False
        self._on_confirm_callback = None
        self._on_cancel_callback = None
        if self.page:
            self.page.update()

    def _handle_confirm(self, e=None):
        cb = self._on_confirm_callback
        self._on_confirm_callback = None
        self._on_cancel_callback = None
        if cb:
            cb()
        self._close_dialog()

    def _handle_cancel(self, e=None):
        cb = self._on_cancel_callback
        self._on_confirm_callback = None
        self._on_cancel_callback = None
        if cb:
            cb()
        self._close_dialog()
