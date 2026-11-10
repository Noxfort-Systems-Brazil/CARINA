# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Any, Callable, Dict, Type

import flet as ft

from ui.widgets.traffic_light_widget import TrafficLightWidget


class MapElementFactory:
    """
    Factory for creating interactive map elements (OCP compliant).
    New elements can be registered without modifying this class.
    """

    _registry: Dict[str, Callable[[str, float, float], ft.Control]] = {}

    @classmethod
    def register_element(cls, node_type: str, builder: Callable[[str, float, float], ft.Control]):
        cls._registry[node_type] = builder

    @classmethod
    def create_element(cls, node_type: str, node_id: str, tx: float, ty: float) -> ft.Control | None:
        builder = cls._registry.get(node_type)
        if builder:
            return builder(node_id, tx, ty)
        return None


# Register known elements
def _build_traffic_light(node_id: str, tx: float, ty: float) -> ft.Control:
    widget = TrafficLightWidget(semaphore_id=node_id)
    widget.left = tx - (widget.width / 2)
    widget.top = ty - (widget.height / 2)
    return widget


MapElementFactory.register_element("traffic_light", _build_traffic_light)
