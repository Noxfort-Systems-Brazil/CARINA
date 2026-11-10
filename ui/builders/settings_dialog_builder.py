# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Any, Callable, Tuple

import flet as ft

from ui.dialogs.confirmation_dialog_manager import ConfirmationDialogManager


class SettingsDialogBuilder:
    """
    Builder responsible for constructing the modal Settings AlertDialog and
    handling security authentication callbacks.
    """

    @staticmethod
    def build_settings_dialog(
        page: ft.Page, locale_manager: Any, security_ui: Any, settings_view: Any, settings_client: Any
    ) -> Tuple[ft.AlertDialog, Callable[[Any], None]]:
        """
        Constructs and mounts the settings modal AlertDialog on page.overlay.

        Args:
            page (ft.Page): Active Flet page instance.
            locale_manager (Any): LocaleManager instance for i18n strings.
            security_ui (Any): SecurityUI instance for requesting operator authentication.
            settings_view (Any): Settings view control component.
            settings_client (Any): SettingsClient instance for backend commands.

        Returns:
            Tuple[ft.AlertDialog, Callable]: (settings_dialog, open_settings_dialog_callback)
        """
        settings_view.page = page
        if not getattr(settings_view, "dialog_manager", None):
            settings_view.dialog_manager = ConfirmationDialogManager(page, locale_manager)

        def _close_immediately():
            settings_dialog.open = False
            page.update()

        def _discard_and_close():
            if not getattr(settings_view, "_is_saving", False) and hasattr(settings_view, "discard_changes"):
                settings_view.discard_changes()
            _close_immediately()

        def close_settings_dialog(e=None):
            if getattr(settings_view, "_is_saving", False):
                return
            if hasattr(settings_view, "has_unsaved_changes") and settings_view.has_unsaved_changes():
                if settings_view.dialog_manager:
                    settings_view.dialog_manager.show_unsaved_changes(
                        on_save=lambda: settings_view.save_and_close(on_close=_close_immediately),
                        on_discard=_discard_and_close,
                        on_cancel=None,
                    )
                    return

            _discard_and_close()

        def _on_dialog_dismiss(e):
            if not getattr(settings_view, "_is_saving", False) and hasattr(settings_view, "discard_changes"):
                settings_view.discard_changes()

        settings_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.SETTINGS),
                    ft.Text(locale_manager.get_string("settings_view.title", default="Configurações")),
                ]
            ),
            content=settings_view,
            actions=[
                ft.TextButton(
                    locale_manager.get_string("dialogs.close_button", default="Fechar"), on_click=close_settings_dialog
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            on_dismiss=_on_dialog_dismiss,
        )
        page.overlay.append(settings_dialog)

        def open_settings_dialog(e=None):
            def _open():
                if not getattr(settings_view, "_is_saving", False) and hasattr(settings_view, "discard_changes"):
                    settings_view.discard_changes()
                settings_dialog.open = True
                if settings_client and hasattr(settings_client, "live_data_provider"):
                    settings_client.live_data_provider.send_command_to_backend({"type": "list_users"})
                page.update()

            if security_ui and hasattr(security_ui, "request_auth"):
                security_ui.request_auth(on_success=_open)
            else:
                _open()

        return settings_dialog, open_settings_dialog
