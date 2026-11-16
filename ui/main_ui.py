# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import os
import sys
import threading
import traceback

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

import flet as ft

from src.utils.logging_setup import setup_logging
from src.utils.paths import get_base_output_dir
from ui.builders.settings_configurator import build_settings_view
from ui.builders.settings_dialog_builder import SettingsDialogBuilder
from ui.clients.control_client import ControlClient
from ui.clients.settings_client import SettingsClient
from ui.handlers.locale_manager import LocaleManager
from ui.handlers.network_event_handler import NetworkEventHandler
from ui.managers.navigation_manager import NavigationManager
from ui.managers.window_manager import WindowManager
from ui.overlays.security_overlay import SecurityUI
from ui.providers.live_data_provider import LiveDataProvider
from ui.views.dashboard_view import DashboardView
from ui.views.diagnostics_view import DiagnosticsView
from ui.views.error_view import ErrorView
from ui.views.planning_view import PlanningView

sas_result_queue = None
mfd_result_queue = None
mfd_trigger_queue = None
ui_telemetry_queue = None
ui_command_queue = None


def main(page: ft.Page):
    """Main function configuring and assembling the Flet application UI."""
    global active_page
    active_page = page

    try:
        # 1. Logging Initialization
        log_base_dir = get_base_output_dir()
        log_dir = os.path.join(log_base_dir, "logs", "ui_worker")
        os.makedirs(log_dir, exist_ok=True)
        setup_logging(log_dir=log_dir)

        logging.info("--- O PROGRAMA DA UI INICIOU COM SUCESSO ---")

        try:
            from src.controller.map_discoverer import MapTopologyDiscoverer
            from src.utils.episode_step_calculator import EpisodeStepCalculator

            map_file = MapTopologyDiscoverer.get_map_file()
            if map_file and os.path.exists(map_file):
                pacing = EpisodeStepCalculator.calculate(map_file)
                logging.info(
                    f"[UI PACING] 1 episódio = {pacing.episode_steps} passos ({pacing.duration_seconds:.1f}s). "
                    f"Piso de segurança (1 semana): {pacing.child_episodes_1_week} episódios."
                )
        except Exception as e_ui_pacing:
            logging.debug(f"[UI PACING] Detecção de pacing inicial ignorada: {e_ui_pacing}")

        locale_manager = LocaleManager()

        current_module = sys.modules[__name__]
        if getattr(current_module, "ui_command_queue", ui_command_queue) is not None:
            os.environ.setdefault("CARINA_GATEWAY_ROLE", "remote")

        # 2. Background Hardware Initialization
        hw_manager = None
        try:
            from src.controller.connection_manager import HardwareConnectionManager

            hw_manager = HardwareConnectionManager.get_instance(locale_manager=locale_manager)
        except Exception as err:
            logging.warning(
                f"[main_ui] Non-critical warning initializing HardwareConnectionManager: {err}", exc_info=True
            )

        # 2.1 Background EVP Emergency Fleet Initialization & DB Restoration
        try:
            from src.evp.evp_service import EVPService

            evp_service = EVPService.get_instance()
            evp_service.restore_saved_fleet_async()
        except Exception as err:
            logging.warning(f"[main_ui] Non-critical warning initializing EVPService fleet: {err}", exc_info=True)

        # 3. Window Manager Configuration
        current_module = sys.modules[__name__]
        restore_ev = getattr(current_module, "restore_event", None)
        shutdown_ev = getattr(current_module, "shutdown_event", None)
        telem_q = getattr(current_module, "ui_telemetry_queue", ui_telemetry_queue)
        cmd_q = getattr(current_module, "ui_command_queue", ui_command_queue)

        window_manager = WindowManager(page, restore_event=restore_ev, shutdown_event=shutdown_ev)

        caminho_do_icone = os.path.join(project_root, "ui", "assets", "images", "logo.ico")
        if not os.path.exists(caminho_do_icone):
            caminho_do_icone = os.path.join(project_root, "ui", "assets", "images", "logo.png")

        window_manager.configure_window(
            app_title=locale_manager.get_string("main_ui.app_title", default="CARINA"), favicon_path=caminho_do_icone
        )

        # 4. Clients, Providers and Security Setup
        live_data_provider = LiveDataProvider(
            on_data_received=lambda data: net_event_handler.handle_sds_data(data),
            shutdown_event=shutdown_ev,
            ui_telemetry_queue=telem_q,
            ui_command_queue=cmd_q,
        )
        control_client = ControlClient(live_data_provider=live_data_provider)
        settings_client = SettingsClient(live_data_provider=live_data_provider)
        security_ui = SecurityUI(page, control_client, locale_manager)

        # 5. Views Assembly
        dashboard_view = DashboardView(
            control_client=control_client, locale_manager=locale_manager, security_ui=security_ui
        )
        page.dashboard_view = dashboard_view
        planning_view = PlanningView(
            locale_manager=locale_manager, control_client=control_client, sas_result_queue=sas_result_queue
        )
        diagnostics_view = DiagnosticsView(locale_manager=locale_manager, control_client=control_client)
        settings_view = build_settings_view(locale_manager, settings_client)

        # 5.1 Auto-start Go Hardware & Web Gateway (Port 2201) and Tailscale Funnel in background
        def _auto_start_go_gateway():
            try:
                from src.drivers.go_gateway_client import GoGatewayClient

                if GoGatewayClient.is_remote_gateway_role():
                    logging.info(
                        "[main_ui] Go Gateway gerenciado pelo CentralController (papel remote). Ignorando auto-início na UI."
                    )
                    return

                client = GoGatewayClient.get_instance()
                client.start()

                try:
                    from src.drivers.go_process_manager import sync_gateway_security_tokens
                    from src.utils.settings_manager import SettingsManager

                    settings_mgr = SettingsManager()
                    is_enabled_bool = settings_mgr.get_bool("gateway_enabled", default=False)
                    sync_gateway_security_tokens(client)

                    if is_enabled_bool:
                        client.send_command("tailscale_enable", timeout=10.0, port=2201)

                    res = client.send_command(
                        "gateway_set_enabled",
                        timeout=8.0,
                        enabled=is_enabled_bool,
                    )
                    logging.info(
                        f"[main_ui] Go Web Gateway estado inicial configurado: enabled={is_enabled_bool} (resp: {res.get('success')})"
                    )
                except Exception as sync_ex:
                    logging.warning(f"[main_ui] Tailscale/Gateway auto-sync ignorado/falhou: {sync_ex}", exc_info=True)
            except Exception as ex:
                logging.warning(f"[main_ui] Não foi possível auto-iniciar GoGatewayClient: {ex}", exc_info=True)

        threading.Thread(target=_auto_start_go_gateway, daemon=True, name="GoGatewayAutoStartThread").start()

        # 5.2 Auto-start SDS Process in background if not already running
        def _auto_start_sds_cco():
            try:
                if ui_command_queue is not None:
                    logging.info(
                        "[main_ui] SDS/CCO já orquestrado pelo ProcessManager. Ignorando auto-início standalone."
                    )
                    return
                from src.sds.sds_process_starter import SDSProcessStarter

                SDSProcessStarter.get_instance().start_if_not_running()
            except Exception as ex:
                logging.warning(f"[main_ui] Não foi possível auto-iniciar SDS/CCO: {ex}", exc_info=True)

        threading.Thread(target=_auto_start_sds_cco, daemon=True, name="SDSAutoStartThread").start()

        # 6. Network Event Handler Setup
        net_event_handler = NetworkEventHandler(
            page=page,
            dashboard_view=dashboard_view,
            security_ui=security_ui,
            settings_view=settings_view,
            locale_manager=locale_manager,
        )

        if hw_manager and hasattr(hw_manager, "event_listener") and hw_manager.event_listener:
            hw_manager.event_listener.on_event_callback = lambda evt: net_event_handler.handle_hardware_trap(evt)

        # 7. Modal Settings Dialog Setup
        settings_dialog, open_settings_dialog = SettingsDialogBuilder.build_settings_dialog(
            page=page,
            locale_manager=locale_manager,
            security_ui=security_ui,
            settings_view=settings_view,
            settings_client=settings_client,
        )

        # 8. Navigation & Tab Manager Setup
        nav_manager = NavigationManager(
            page=page,
            locale_manager=locale_manager,
            dashboard_view=dashboard_view,
            planning_view=planning_view,
            diagnostics_view=diagnostics_view,
            settings_view=settings_view,
            settings_dialog=settings_dialog,
            open_settings_callback=open_settings_dialog,
        )

        page.appbar = nav_manager.appbar

        def on_disconnect(e):
            logging.info("--- O PROGRAMA DA UI FOI ENCERRADO ---")
            if shutdown_ev:
                shutdown_ev.set()
            if live_data_provider:
                live_data_provider.stop()
            try:
                if evp_receiver:
                    evp_receiver.stop()
            except Exception:
                pass
            try:
                from src.communication.monitor_client import MonitorClient

                if MonitorClient._instance and MonitorClient._instance.enabled:
                    MonitorClient._instance.stop(shutdown_message="Operador encerrou a interface da CARINA_CORE")
            except Exception as err:
                logging.error(f"[main_ui] Exception sending Monitor shutdown message: {err}", exc_info=True)
            try:
                from src.sds.sds_process_starter import SDSProcessStarter

                SDSProcessStarter.get_instance().stop()
            except Exception:
                pass

        page.on_disconnect = on_disconnect
        live_data_provider.start()

        page.add(nav_manager.tabs)
        nav_manager.apply_translations()
        page.update()

    except Exception as err:
        error_msg = traceback.format_exc()
        logging.error(f"[main_ui] Erro crítico na inicialização da UI: {err}\n{error_msg}", exc_info=True)
        ErrorView.render_error_card(
            page, error_msg, on_restart_callback=lambda e: main(page), locale_manager=locals().get("locale_manager")
        )


if __name__ == "__main__":
    ft.app(target=main)
