# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import os
import queue
import sys
import threading
import time

# 1. Project path setup
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

src_path = os.path.join(project_root, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

import flet as ft
from src.utils.paths import get_base_output_dir
from demo.carina_demo_feed import CarinaDemoFeed
from demo.mock_report_generator import setup_demo_filesystem
import ui.main_ui as ui_module
from ui.overlays.security_overlay import SecurityUI
from ui.dialogs.confirmation_dialog_manager import ConfirmationDialogManager
from ui.components.interactive_map import InteractiveMap
from ui.views.planning_view import PlanningView

PORT = 8550
HOST = "127.0.0.1"


def run_demo():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [DEMO_LAUNCHER] %(message)s",
    )
    logging.info(f"--- INICIANDO CARINA EM MODO APRESENTAÇÃO / WEB ({HOST}:{PORT}) ---")

    # 1. Ensure mock filesystem structure exists (status.json, checkpoints, etc.)
    base_dir = get_base_output_dir()
    setup_demo_filesystem(base_dir)

    # 2. Patch SecurityUI and ConfirmationDialogManager so actions bypass modal barriers in demo mode
    SecurityUI.request_auth = lambda self, on_success: on_success()
    ConfirmationDialogManager.show = lambda self, title, content, on_confirm: on_confirm() if on_confirm else None

    # 2.1 Pre-load EVP emergency fleet from demo CSV
    try:
        from src.evp.evp_fleet_csv_service import EVPFleetCsvService
        from src.evp.evp_service import EVPService
        evp_service = EVPService.get_instance()
        csv_path = os.path.join(os.path.dirname(__file__), "frota_exemplo_evp.csv")
        if os.path.exists(csv_path):
            vehicles, count = EVPFleetCsvService.parse_csv_file(csv_path)
            for v in vehicles:
                evp_service.register_fleet_vehicle(v)
            logging.info(f"[DEMO_LAUNCHER] 🚑 Frota de emergência carregada: {len(evp_service.get_all_vehicles())} viaturas cadastradas.")
    except Exception as ex:
        logging.warning(f"[DEMO_LAUNCHER] Não foi possível pré-carregar frota EVP: {ex}")

    # 2.2 Pre-enable Go Hardware Gateway for CCO broadcast and EVP telemetry
    try:
        from src.drivers.go_gateway_client import GoGatewayClient
        gw_client = GoGatewayClient.get_instance()
        if not gw_client.is_running():
            gw_client.start()
        gw_client.send_command("gateway_set_enabled", enabled=True)
    except Exception as ex:
        logging.debug(f"[DEMO_LAUNCHER] GoGatewayClient notice: {ex}")

    # 3. Safe patches for InteractiveMap & PlanningView to avoid unmounted update() errors in headless mode
    def safe_load_map(self):
        map_data = self.asset_loader.load_map_data()
        if map_data:
            nodes, edges, bounds = map_data
            self.topology = {"nodes": nodes, "edges": edges, "bounds": bounds}
            self.renderer.calculate_initial_fit(self.topology)
            self._draw()
            if getattr(self, "page", None):
                try:
                    self.update()
                except Exception:
                    pass
            if self.on_topology_loaded:
                try:
                    self.on_topology_loaded()
                except Exception as ex:
                    logging.debug(f"[InteractiveMap Orchestrator] Error calling on_topology_loaded: {ex}")

    InteractiveMap.load_map = safe_load_map

    def safe_pv_topo(self):
        if self.map_widget and self.planning_control_panel and self.map_widget.topology:
            self.planning_control_panel.set_topology(self.map_widget.topology)
        if self.is_analyzing:
            return
        self.analyze_button.disabled = False
        self.command_bar_widget.set_status("Topologia carregada. Pronto para análise.", italic=True)
        if getattr(self, "page", None):
            try:
                self.update()
            except Exception:
                pass

    PlanningView._on_topology_loaded = safe_pv_topo

    # 4. Setup queues
    telemetry_q = queue.Queue()
    command_q = queue.Queue()
    sas_q = queue.Queue()
    mfd_q = queue.Queue()
    mfd_trig_q = queue.Queue()

    shutdown_event = threading.Event()

    # 5. Inject queues into ui_module
    ui_module.ui_telemetry_queue = telemetry_q
    ui_module.ui_command_queue = command_q
    ui_module.sas_result_queue = sas_q
    ui_module.mfd_result_queue = mfd_q
    ui_module.mfd_trigger_queue = mfd_trig_q
    ui_module.shutdown_event = shutdown_event

    # 6. Start Demo Feed Simulator
    feed_sim = CarinaDemoFeed(
        ui_telemetry_queue=telemetry_q,
        ui_command_queue=command_q,
        sas_result_queue=sas_q,
        mfd_trigger_queue=mfd_trig_q,
        mfd_result_queue=mfd_q,
        shutdown_event=shutdown_event,
    )
    feed_sim.start()

    # 7. Environment configuration for Headless Web Server
    os.environ["FLET_SERVER_PORT"] = str(PORT)
    os.environ["FLET_SERVER_IP"] = HOST
    os.environ["FLET_FORCE_WEB_SERVER"] = "true"
    os.environ["FLET_DISPLAY_URL_PREFIX"] = "CARINA_WEB_READY:"

    assets_dir = os.path.join(project_root, "ui", "assets")

    orig_main = ui_module.main

    def demo_target(page: ft.Page):
        orig_main(page)

        # Hook PlanningView and DiagnosticsView
        for ctrl in page.controls:
            if isinstance(ctrl, ft.Tabs) and len(ctrl.tabs) > 2:
                # Tab 1: PlanningView
                pv = ctrl.tabs[1].content
                if hasattr(pv, "command_bar_widget"):
                    pv.command_bar_widget.analyze_button.disabled = False
                    pv.command_bar_widget.set_status("Topologia carregada. Pronto para análise.", italic=True)

                # Tab 2: DiagnosticsView
                dv = ctrl.tabs[2].content
                if hasattr(dv, "xai_viewer"):
                    dv.xai_viewer.update_agent_list(["1116667894", "1193472473", "1193472566", "1193472678"])

        page.update()

    try:
        ft.app(
            target=demo_target,
            host=HOST,
            port=PORT,
            view=None,
            assets_dir=assets_dir,
            web_renderer=ft.WebRenderer.CANVAS_KIT,
        )
    except KeyboardInterrupt:
        logging.info("[DEMO_LAUNCHER] Encerrando...")
    finally:
        feed_sim.stop()
        shutdown_event.set()


if __name__ == "__main__":
    run_demo()
