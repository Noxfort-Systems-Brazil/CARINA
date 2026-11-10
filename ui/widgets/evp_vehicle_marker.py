# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Emergency Vehicle Visual Marker on Flet Canvas / Map.
Renders Triangle (SAMU), Square (Firefighters), and Circle (Police)
with blinking color animation in alert mode and click-to-inspect behavior.
"""

from typing import Any, Callable, Dict, Optional
import flet as ft
import flet.canvas as cv


class EVPVehicleMarker(ft.Container):
    """
    Interactive map component representing an emergency vehicle.
    """

    def __init__(
        self,
        vehicle_id: str,
        corporation: str,
        initial_lat: float,
        initial_lon: float,
        siren_active: bool = False,
        speed_kmh: float = 0.0,
        heading_deg: float = 0.0,
        is_evp_triggered: bool = False,
        on_click_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        super().__init__()

        self.vehicle_id = vehicle_id
        self.corporation = corporation.upper()
        self.latitude = initial_lat
        self.longitude = initial_lon
        self.siren_active = siren_active
        self.is_evp_triggered = is_evp_triggered
        self.speed_kmh = speed_kmh
        self.heading_deg = heading_deg
        self.on_click_callback = on_click_callback

        self.width = 16
        self.height = 16
        self.alignment = ft.alignment.center
        self.animate_position = 300

        self.base_color, self.alert_color = self._get_colors()
        is_alert = self.siren_active or self.is_evp_triggered
        self.current_fill_color = self.alert_color if is_alert else self.base_color

        self.fill_paint: Optional[ft.Paint] = None
        self.fill_shape: Optional[cv.Shape] = None
        self.shape_canvas = self._build_shape_canvas()
        self.content = self.shape_canvas
        self.on_click = self._handle_click

    def _get_colors(self):
        """Returns base and alert colors by corporation."""
        if "SAMU" in self.corporation:
            return ("#FFFFFF", "#E53935")  # White and Bright Red
        elif "BOMB" in self.corporation:
            return ("#FF9800", "#FF3D00")  # Orange and Fire Red
        return ("#1E3A8A", "#2563EB")       # Dark Blue and Bright Blue (Police)

    def _build_shape_canvas(self) -> ft.Control:
        """Constructs geometric shape: Triangle (SAMU), Square (Firefighters), Circle (Police)."""
        w, h = 16.0, 16.0
        self.fill_paint = ft.Paint(
            color=self.current_fill_color,
            style=ft.PaintingStyle.FILL,
        )

        if "SAMU" in self.corporation:
            # Triangle (SAMU)
            path = cv.Path(
                elements=[
                    cv.Path.MoveTo(w / 2.0, 1.0),
                    cv.Path.LineTo(w - 1.0, h - 1.0),
                    cv.Path.LineTo(1.0, h - 1.0),
                    cv.Path.Close(),
                ],
                paint=self.fill_paint,
            )
            border_path = cv.Path(
                elements=[
                    cv.Path.MoveTo(w / 2.0, 1.0),
                    cv.Path.LineTo(w - 1.0, h - 1.0),
                    cv.Path.LineTo(1.0, h - 1.0),
                    cv.Path.Close(),
                ],
                paint=ft.Paint(
                    color=ft.Colors.BLACK,
                    stroke_width=1.5,
                    style=ft.PaintingStyle.STROKE,
                ),
            )
            self.fill_shape = path
            return cv.Canvas([path, border_path], width=w, height=h)

        elif "BOMB" in self.corporation:
            # Square (Firefighters)
            rect = cv.Rect(
                x=1.5,
                y=1.5,
                width=w - 3.0,
                height=h - 3.0,
                border_radius=2.0,
                paint=self.fill_paint,
            )
            border_rect = cv.Rect(
                x=1.5,
                y=1.5,
                width=w - 3.0,
                height=h - 3.0,
                border_radius=2.0,
                paint=ft.Paint(
                    color=ft.Colors.BLACK,
                    stroke_width=1.5,
                    style=ft.PaintingStyle.STROKE,
                ),
            )
            self.fill_shape = rect
            return cv.Canvas([rect, border_rect], width=w, height=h)

        else:
            # Circle (Police)
            circle = cv.Circle(
                x=w / 2.0,
                y=h / 2.0,
                radius=(w / 2.0) - 1.5,
                paint=self.fill_paint,
            )
            border_circle = cv.Circle(
                x=w / 2.0,
                y=h / 2.0,
                radius=(w / 2.0) - 1.5,
                paint=ft.Paint(
                    color=ft.Colors.BLACK,
                    stroke_width=1.5,
                    style=ft.PaintingStyle.STROKE,
                ),
            )
            self.fill_shape = circle
            return cv.Canvas([circle, border_circle], width=w, height=h)

    def update_state(
        self,
        lat: float,
        lon: float,
        speed_kmh: float,
        heading_deg: float,
        siren_active: bool,
        blink_state: bool,
        is_evp_triggered: bool = False,
    ) -> None:
        """Updates dynamic position and blinking color effect in-place on Canvas."""
        self.latitude = lat
        self.longitude = lon
        self.speed_kmh = speed_kmh
        self.heading_deg = heading_deg
        self.siren_active = siren_active
        self.is_evp_triggered = is_evp_triggered

        is_alert = self.siren_active or self.is_evp_triggered

        # If in alert (siren or active preemption), color alternates (blinks) between alert and base
        if is_alert:
            self.current_fill_color = self.alert_color if blink_state else self.base_color
        else:
            self.current_fill_color = self.base_color

        # Modify paint in-place without recreating Canvas (avoids AssertionError in Flet)
        if self.fill_paint is not None:
            self.fill_paint.color = self.current_fill_color
        elif self.fill_shape is not None and hasattr(self.fill_shape, "paint"):
            self.fill_shape.paint = ft.Paint(
                color=self.current_fill_color,
                style=ft.PaintingStyle.FILL,
            )

        if getattr(self, "page", None):
            try:
                if self.shape_canvas and getattr(self.shape_canvas, "page", None):
                    self.shape_canvas.update()
                else:
                    self.update()
            except Exception:
                try:
                    self.update()
                except Exception:
                    pass

    def _handle_click(self, e):
        """On marker click, triggers callback with full vehicle telemetry data."""
        if self.on_click_callback:
            self.on_click_callback({
                "vehicle_id": self.vehicle_id,
                "corporation": self.corporation,
                "latitude": self.latitude,
                "longitude": self.longitude,
                "speed_kmh": self.speed_kmh,
                "heading_deg": self.heading_deg,
                "siren_active": self.siren_active,
                "is_evp_triggered": self.is_evp_triggered,
            })
