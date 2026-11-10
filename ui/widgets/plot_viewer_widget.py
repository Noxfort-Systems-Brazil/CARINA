# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import os

import flet as ft

from ui.handlers.locale_manager import LocaleManager


class PlotViewerWidget(ft.Container):
    """
    Widget dedicated to displaying the XAI chart (image).
    Handles hiding/showing the image and refreshing the source properly.
    """

    def __init__(self, locale_manager: LocaleManager):
        super().__init__()
        self.locale_manager = locale_manager

        # --- FIX: Renamed from self.image to self.plot_image to avoid collision ---
        # ft.Container already has a property named 'image' for background images.
        # Overwriting it with a Control causes a Circular Reference error during serialization.
        self.plot_image = ft.Image(
            src="", fit=ft.ImageFit.CONTAIN, visible=False, gapless_playback=True, expand=True  # Starts invisible
        )

        # Placeholder (Text/Icon showed when no image is loaded)
        self.placeholder_icon = ft.Icon(ft.Icons.INSERT_CHART_OUTLINED, size=64, color=ft.Colors.GREY_700)
        self.placeholder_text = ft.Text(
            value=self.locale_manager.get_string("plot_viewer.no_data", default="No analysis generated yet."),
            color=ft.Colors.GREY_500,
            text_align=ft.TextAlign.CENTER,
        )

        self.placeholder_col = ft.Column(
            controls=[self.placeholder_icon, self.placeholder_text],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            visible=True,
        )

        # Layout
        self.content = ft.Stack(
            controls=[self.placeholder_col, self.plot_image], alignment=ft.alignment.center  # Updated reference
        )

        # styles
        self.expand = True
        self.bgcolor = ft.Colors.BLACK12
        self.border = ft.border.all(1, ft.Colors.GREY_800)
        self.border_radius = 8
        self.padding = 20
        self.alignment = ft.alignment.center

    def load_plot(self, image_path: str):
        """
        Updates the displayed image.
        If image_path is None or invalid, shows the placeholder.
        """
        if image_path and os.path.exists(image_path):
            # Update image source
            self.plot_image.src = os.path.abspath(image_path)
            self.plot_image.visible = True

            # Hide placeholder
            self.placeholder_col.visible = False
        else:
            # clear image
            self.plot_image.src = ""
            self.plot_image.visible = False

            # Show placeholder
            self.placeholder_col.visible = True

        # Force UI update for this specific widget
        self.update()

    def load_plot_base64(self, base64_str: str):
        """
        Updates the displayed image using base64 representation.
        """
        if base64_str:
            self.plot_image.src_base64 = base64_str
            self.plot_image.visible = True
            self.placeholder_col.visible = False
        else:
            self.plot_image.src_base64 = None
            self.plot_image.visible = False
            self.placeholder_col.visible = True
        self.update()

    def update_translations(self, locale_manager: LocaleManager):
        """Refreshes text translations."""
        self.locale_manager = locale_manager
        self.placeholder_text.value = locale_manager.get_string(
            "plot_viewer.no_data", default="No analysis generated yet."
        )
        self.update()
