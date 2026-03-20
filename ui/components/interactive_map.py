# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2025 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# File: ui/components/interactive_map.py (Updated: Streets colored Black)
# Author: Gabriel Moraes
# Date: December 16, 2025

import flet as ft
import flet.canvas as cv
import json
import os
import math

from ui.handlers.map_interaction_handler import MapInteractionHandler

class InteractiveMap(ft.Container):
    """
    Interactive Vector Map Component.
    Displays the network topology with traffic lights (blue icons) and simple junctions (orange dots).
    Reads data from 'results/hft_live_session/maps/map_topology.json'.
    """

    def __init__(self, project_root: str, on_node_click=None):
        super().__init__(expand=True)
        
        self.project_root = project_root
        self.on_node_click = on_node_click 
        
        self.topology = None
        self.drawn_nodes_cache = [] 
        
        # Base Dimensions for scale calculation
        self.base_width = 1200
        self.base_height = 800
        
        self.fit_scale = 1.0
        self.fit_offset_x = 0
        self.fit_offset_y = 0
        
        # --- Visual Config ---
        # Street color set to BLACK as requested
        self.street_color = ft.Colors.BLACK
        self.street_width = 4.5
        
        # Traffic Lights (Blue Body, Standard Lights)
        self.tl_box_color = ft.Colors.BLUE_800 
        self.tl_light_colors = [ft.Colors.RED, ft.Colors.AMBER, ft.Colors.GREEN]
        self.hit_radius = 25.0 
        
        # Simple Junctions (Medium Orange Dot)
        self.junction_color = ft.Colors.ORANGE_600
        self.junction_radius = 6.0 

        # Architecture (Stack + Handler for Zoom/Pan)
        self.interaction_handler = MapInteractionHandler(on_update_callback=self.update)
        self.canvas = cv.Canvas(shapes=[], expand=True)

        # Stack container with explicit size to ensure drawing area
        self.map_stack = ft.Stack(
            controls=[self.canvas],
            width=self.base_width,
            height=self.base_height,
            scale=self.interaction_handler.scale,
            offset=self.interaction_handler.offset,
        )

        self.gesture_detector = ft.GestureDetector(
            # Container wraps the Stack and fills available space with background color
            content=ft.Container(
                content=self.map_stack, 
                bgcolor="#F7F7F7",
                alignment=ft.alignment.center # Centers the map on screen
            ),
            on_pan_update=self.interaction_handler.handle_pan_update,
            on_scroll=self.interaction_handler.handle_zoom,
            on_double_tap=lambda e: self.interaction_handler.center_and_reset_zoom(),
            on_tap_down=self._handle_tap,
            drag_interval=10
        )

        self.content = self.gesture_detector
        self.bgcolor = "#F7F7F7"
        self.clip_behavior = ft.ClipBehavior.HARD_EDGE
        self.border_radius = 10

    def load_map(self):
        """Reads topology JSON and triggers redraw."""
        # Expected path: results/hft_live_session/maps/map_topology.json
        from src.utils.paths import get_base_output_dir
        json_path = os.path.join(get_base_output_dir(), "results", "hft_live_session", "maps", "map_topology.json")
        
        if not os.path.exists(json_path):
            print(f"[InteractiveMap] FILE NOT FOUND: {json_path}")
            print(f"[InteractiveMap] Check if Backend generated the map in the correct folder.")
            return

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                self.topology = json.load(f)
            
            print(f"[InteractiveMap] JSON loaded. Starting processing...")
            self._calculate_initial_fit()
            self._draw()
            
            # Center map visually
            self.interaction_handler.center_and_reset_zoom()
            self.update()
            print(f"[InteractiveMap] Map drawn successfully.")
        except Exception as e:
            print(f"[InteractiveMap] CRITICAL ERROR loading map: {e}")

    def _calculate_initial_fit(self):
        if not self.topology: return
        
        try:
            bounds = self.topology.get('bounds')
            if not bounds:
                print("[InteractiveMap] Warning: 'bounds' not found in JSON.")
                return

            min_x, min_y = bounds['min_x'], bounds['min_y']
            max_x, max_y = bounds['max_x'], bounds['max_y']
            
            map_w = max_x - min_x
            map_h = max_y - min_y
            if map_w == 0: map_w = 1
            if map_h == 0: map_h = 1

            scale_x = self.base_width / map_w
            scale_y = self.base_height / map_h
            self.fit_scale = min(scale_x, scale_y) * 0.95 
            
            pixel_map_w = map_w * self.fit_scale
            pixel_map_h = map_h * self.fit_scale
            
            self.fit_offset_x = (self.base_width - pixel_map_w) / 2
            self.fit_offset_y = (self.base_height - pixel_map_h) / 2
        except Exception as e:
            print(f"[InteractiveMap] Error calculating fit scale: {e}")

    def _map_to_canvas(self, mx, my):
        try:
            bounds = self.topology['bounds']
            rel_x = mx - bounds['min_x']
            rel_y_flipped = bounds['max_y'] - my
            cx = self.fit_offset_x + (rel_x * self.fit_scale)
            cy = self.fit_offset_y + (rel_y_flipped * self.fit_scale)
            return cx, cy
        except:
            return 0, 0

    def _create_traffic_light_icon(self, sx, sy):
        """Draws vector traffic light icon (Blue Box + Standard Lights)."""
        shapes = []
        
        # Dimensions (Medium Size)
        box_w, box_h = 16, 42 
        light_radius = 5 
        spacing = 11 
        
        # Traffic Light Box (Blue Body)
        shapes.append(cv.Rect(
            x=sx - box_w/2, y=sy - box_h/2,
            width=box_w, height=box_h,
            border_radius=4,
            paint=ft.Paint(color=self.tl_box_color, style=ft.PaintingStyle.FILL)
        ))
        
        # Lights (Red, Amber, Green)
        y_offsets = [-spacing, 0, spacing]
        for i in range(3):
             shapes.append(cv.Circle(
                x=sx, y=sy + y_offsets[i],
                radius=light_radius,
                paint=ft.Paint(color=self.tl_light_colors[i], style=ft.PaintingStyle.FILL)
            ))
        return shapes

    def _draw(self):
        """
        Draws edges and nodes on Canvas.
        Includes robust logic to handle different JSON formats (list vs dict).
        """
        if not self.topology: return
        
        self.canvas.shapes.clear()
        self.drawn_nodes_cache.clear()

        # ---------------------------------------------------------
        # 1. Streets (Edges)
        # ---------------------------------------------------------
        edges_data = self.topology.get('edges', [])
        
        # Normalize to iterator, whether list or dict
        if isinstance(edges_data, dict):
            edges_iter = edges_data.values()
        elif isinstance(edges_data, list):
            edges_iter = edges_data
        else:
            edges_iter = []

        for edge_item in edges_iter:
            if not edge_item: continue
            
            try:
                # If dict, try getting 'shape'. If list, assume it is the shape itself.
                if isinstance(edge_item, dict):
                    shape_points = edge_item.get('shape')
                else:
                    shape_points = edge_item
                
                if not shape_points or len(shape_points) < 2: 
                    continue
                
                points = []
                # Start point (MoveTo)
                start_x, start_y = self._map_to_canvas(shape_points[0][0], shape_points[0][1])
                points.append(cv.Path.MoveTo(start_x, start_y))
                
                # Rest of points (LineTo)
                for coord in shape_points[1:]:
                    cx, cy = self._map_to_canvas(coord[0], coord[1])
                    points.append(cv.Path.LineTo(cx, cy))
                    
                self.canvas.shapes.append(
                    cv.Path(
                        elements=points,
                        paint=ft.Paint(
                            color=self.street_color,
                            stroke_width=self.street_width,
                            stroke_cap=ft.StrokeCap.ROUND, 
                            style=ft.PaintingStyle.STROKE
                        )
                    )
                )
            except Exception as e:
                # Ignore problematic edges without breaking the rest
                print(f"[InteractiveMap] Error drawing specific edge: {e}")
                continue

        # ---------------------------------------------------------
        # 2. Nodes (Traffic Lights and Junctions)
        # ---------------------------------------------------------
        nodes_data = self.topology.get('nodes', [])
        
        if isinstance(nodes_data, dict):
            nodes_iter = nodes_data.values()
        elif isinstance(nodes_data, list):
            nodes_iter = nodes_data
        else:
            nodes_iter = []

        for node in nodes_iter:
            try:
                # Ensure we have coordinates
                if 'x' not in node or 'y' not in node:
                    continue

                cx, cy = self._map_to_canvas(node['x'], node['y'])
                node_type = node.get('type', '')
                
                # Logic to identify traffic light
                is_traffic_light = False
                if node_type is None:
                    is_traffic_light = True # Assume default if null
                elif "traffic_light" in str(node_type):
                    is_traffic_light = True
                
                if is_traffic_light:
                    # Store cache for click
                    node_id = node.get('id', 'unknown')
                    self.drawn_nodes_cache.append({
                        "id": node_id,
                        "cx": cx, "cy": cy 
                    })
                    
                    # Draw complex icon
                    icon_shapes = self._create_traffic_light_icon(cx, cy)
                    self.canvas.shapes.extend(icon_shapes)
                    
                else:
                    # Simple Junction
                    self.canvas.shapes.append(
                        cv.Circle(
                            x=cx, y=cy,
                            radius=self.junction_radius,
                            paint=ft.Paint(color=self.junction_color, style=ft.PaintingStyle.FILL)
                        )
                    )
            except Exception as e:
                print(f"[InteractiveMap] Error drawing specific node: {e}")
                continue

    def _handle_tap(self, e: ft.TapEvent):
        """Detects click on traffic lights using position cache."""
        scale = self.interaction_handler.scale.scale
        offset = self.interaction_handler.offset
        
        center_x = self.base_width / 2 
        center_y = self.base_height / 2
        
        click_x, click_y = e.local_x, e.local_y
        
        clicked_node_id = None
        min_dist = float('inf')
        
        effective_scale = scale
        # Offset in Flet is relative to control size
        off_x = offset.x * 1000 
        off_y = offset.y * 1000
        
        for node in self.drawn_nodes_cache:
            # Project node position on screen considering current zoom/pan
            screen_x = (node['cx'] - center_x) * effective_scale + center_x + off_x
            screen_y = (node['cy'] - center_y) * effective_scale + center_y + off_y
            
            dx = click_x - screen_x
            dy = click_y - screen_y
            dist = math.sqrt(dx*dx + dy*dy)
            
            # Click radius increases with zoom to facilitate
            hit = self.hit_radius * effective_scale 
            
            if dist < hit and dist < min_dist:
                min_dist = dist
                clicked_node_id = node['id']

        if clicked_node_id:
            print(f"[InteractiveMap] Click detected on: {clicked_node_id}")
            if self.on_node_click:
                self.on_node_click(clicked_node_id)