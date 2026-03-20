# File: ui/handlers/map_animator.py (FIXED)
# Author: Gabriel Moraes
# Date: October 1, 2025

"""
Define a classe MapAnimator.

Nesta versão, ele assume a responsabilidade de atualizar TODOS os componentes
visuais de alta frequência (mapa e painel de detalhes) dentro do seu loop
controlado, para evitar a sobrecarga da thread da UI.
"""

import flet as ft
import flet.canvas as cv
import logging
import threading
import time
import queue
from typing import Dict, Any, TYPE_CHECKING

from ui.widgets.traffic_light_widget import TrafficLightWidget

# Prevents circular import at runtime, but allows the code editor to understand types
if TYPE_CHECKING:
    from ui.views.dashboard_view import DashboardView
    from ui.widgets.control_panel_widget import ControlPanelWidget

class MapAnimator:
    """
    Gerencia uma thread para aplicar atualizações visuais de alta frequência.
    """
    def __init__(
        self,
        widget_to_update: ft.Control,
        # --- CHANGE 1: Receive references to Dashboard and Control Panel ---
        dashboard_view: 'DashboardView',
        control_panel: 'ControlPanelWidget',
        edge_paths: Dict[str, cv.Path] = None,
        semaforo_widgets: Dict[str, TrafficLightWidget] = None,
        interval: float = 0.5
    ):
        self.widget = widget_to_update
        self.dashboard_view = dashboard_view
        self.control_panel = control_panel
        self.edge_paths = edge_paths or {}
        self.semaforo_widgets = semaforo_widgets or {}
        self.interval = interval
        
        self.thread = None
        self.is_running = False
        
        self.data_lock = threading.Lock()
        self.latest_congestion_data: Dict[str, Dict] = {} 
        self.latest_panel_data: Dict[str, Dict] = {}

        self.command_queue = queue.Queue()
        self.overrides: Dict[str, str] = {}
        self.blink_toggle = False

    def start(self):
        if not self.thread or not self.thread.is_alive():
            self.is_running = True
            self.thread = threading.Thread(target=self._updater_loop, daemon=True)
            self.thread.start()
            logging.info("[MapAnimator] Thread de animação (modo renderização) iniciada.")

    def stop(self):
        self.is_running = False
        logging.info("[MapAnimator] Sinal para parar a thread de animação enviado.")

    def update_data(self, data_packet: dict):
        with self.data_lock:
            if data_packet.get("type") == "initial_map_geometry":
                 self.latest_congestion_data = data_packet.get("congestion_update", {})
            elif data_packet.get("type") == "congestion_update":
                self.latest_congestion_data = data_packet.get("payload", {})
            
            self.latest_panel_data = data_packet.get("panel_data", {})

    def _get_color_for_congestion(self, value: float, max_value: float = 100.0) -> str:
        normalized_value = min(max(value / max_value, 0.0), 1.0)
        red, green, blue = 0, 0, 0
        if normalized_value < 0.25:
            p = normalized_value / 0.25; red = 0; green = int(255 * p); blue = int(128 + 127 * p)
        elif normalized_value < 0.5:
            p = (normalized_value - 0.25) / 0.25; red = 0; green = 255; blue = int(255 * (1 - p))
        elif normalized_value < 0.75:
            p = (normalized_value - 0.5) / 0.25; red = int(255 * p); green = 255; blue = 0
        else:
            p = (normalized_value - 0.75) / 0.25; red = 255; green = int(255 * (1 - p)); blue = 0
        return f"#{red:02x}{green:02x}{blue:02x}"

    def _updater_loop(self):
        """O loop que lê os dados mais recentes e aplica TODAS as atualizações visuais."""
        while self.is_running:
            try:
                self.blink_toggle = not self.blink_toggle

                with self.data_lock:
                    congestion_to_render = self.latest_congestion_data.copy()
                    panel_data_to_render = self.latest_panel_data.copy()

                if self.edge_paths and congestion_to_render:
                    for edge_id, path_object in self.edge_paths.items():
                        congestion_value = congestion_to_render.get(edge_id, 0.0)
                        new_color = self._get_color_for_congestion(congestion_value)
                        path_object.paint.color = new_color

                if self.semaforo_widgets and panel_data_to_render:
                    for semaforo_id, widget in self.semaforo_widgets.items():
                        override_state = self.overrides.get(semaforo_id)
                        if override_state:
                            if override_state == 'ALERT':
                                widget.set_state('YELLOW' if self.blink_toggle else 'OFF')
                            elif override_state == 'OFF':
                                widget.set_state('OFF')
                        else:
                            semaforo_data = panel_data_to_render.get(semaforo_id, {})
                            new_state = semaforo_data.get("display_state", "RED")
                            widget.set_state(new_state)

                # --- CHANGE 2: New responsibility - Update details pane ---
                # Access the state directly from the DashboardView to know which item is selected
                selected_id = getattr(self.dashboard_view, 'selected_semaphore_id', None)
                
                # Only updates the panel if it is visible and a traffic light is selected
                if selected_id and getattr(self.control_panel, 'specific_controls', None) and self.control_panel.specific_controls.visible:
                    semaphore_data = panel_data_to_render.get(selected_id, {})
                    
                    # Security check for maturity_phases dictionary
                    phases_dict = getattr(self.dashboard_view, 'maturity_phases', {})
                    phase = phases_dict.get(selected_id, "UNKNOWN") if phases_dict else "UNKNOWN"
                    
                    mode = getattr(self.dashboard_view, 'current_mode', "UNKNOWN")
                    
                    # Commands update of the details panel (this will call .update() internally)
                    self.control_panel.exibir_controles_semaforo(
                        selected_id,
                        semaphore_data,
                        phase,
                        mode
                    )
                # --- END OF CHANGE 2 ---

                # Major map update still required
                if self.widget and getattr(self.widget, 'page', None):
                    self.widget.update()
                
                time.sleep(self.interval)

            except AssertionError:
                # Flet raises AssertionError when trying to update something that is not already on the page
                logging.info("[MapAnimator Thread] Interface gráfica foi descartada. Encerrando o loop suavemente.")
                self.is_running = False
                break
            except RuntimeError as e:
                # Protection against "Event loop is closed"
                if "Event loop is closed" in str(e) or "shutdown" in str(e):
                    logging.info("[MapAnimator Thread] Event Loop do Flet encerrado. Parando animações.")
                    self.is_running = False
                    break
                else:
                    logging.error(f"[MapAnimator Thread] Erro de Runtime inesperado: {e}")
            except Exception as e:
                logging.error(f"[MapAnimator Thread] Erro: {e}. Encerrando a thread.", exc_info=True)
                self.is_running = False
                break