# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Any, Dict, List, Optional, Tuple

import flet as ft
import flet.canvas as cv

from ui.builders.map_element_factory import MapElementFactory
from ui.interfaces.map_protocols import MapDrawerProtocol


class MapControlsAssembler:
    """
    Assembles Flet Canvas and Interactive elements for the Map Stack.
    """

    def assemble_map_controls(
        self, drawer: MapDrawerProtocol, canvas: cv.Canvas, background_control: Optional[ft.Control] = None
    ) -> Tuple[List[ft.Control], Dict[str, Any]]:
        """
        Creates control instances using the element factory and returns them as a Stack-ready list.
        """
        interactive_widgets_map: Dict[str, Any] = {}
        widgets_list = []

        for node_id, node_data in drawer.nodes.items():
            node_type = node_data.get("type")
            if node_type:
                tx, ty = drawer.transform_point(node_data["x"], node_data["y"])
                widget = MapElementFactory.create_element(node_type, node_id, tx, ty)

                if widget:
                    widgets_list.append(widget)
                    if hasattr(widget, "apply_telemetry"):
                        interactive_widgets_map[node_id] = widget

        stack_controls = []
        if background_control:
            stack_controls.append(background_control)
        stack_controls.append(canvas)
        stack_controls.extend(widgets_list)

        return stack_controls, interactive_widgets_map
