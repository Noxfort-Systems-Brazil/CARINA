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

# File: src/controller/request_processor.py
# Author: Gabriel Moraes
# Date: February 19, 2026

import logging
import os
import sys
import configparser
from multiprocessing import Queue
from multiprocessing.connection import Connection
from queue import Empty, Full
from typing import TYPE_CHECKING, Any

# Add 'src' directory to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend
    from controller.health_monitor import AIHealthMonitor
    from controller.override_manager import OverrideManager
    from controller.failsafe_manager import FailsafeManager
    from controller.topology_manager import TopologyManager

from utils.settings_manager import SettingsManager

class EnvironmentConnectionException(Exception):
    pass

class RequestProcessor:
    def __init__(self, settings: configparser.ConfigParser, ai_pipe_conn: Connection, watchdog_q: Queue,
                 health_monitor: 'AIHealthMonitor', sds_data_queue: Queue,
                 sas_data_queue: Queue, ui_command_queue: Queue,
                 locale_manager: 'LocaleManagerBackend',
                 override_manager: 'OverrideManager',
                 failsafe_manager: 'FailsafeManager',
                 topology_manager: 'TopologyManager'):

        self.settings = settings
        self.ai_pipe_conn = ai_pipe_conn
        self.watchdog_q = watchdog_q
        self.health_monitor = health_monitor
        self.sds_queue = sds_data_queue
        self.sas_queue = sas_data_queue
        self.ui_command_queue = ui_command_queue
        self.locale_manager = locale_manager
        self.override_manager = override_manager
        self.failsafe_manager = failsafe_manager
        self.topology_manager = topology_manager

        self.maturity_phases = {}
        self.current_run_id = None
        self.override_commands_buffer = []

        # --- Latch Callbacks ---
        self.on_ui_ready = None
        self.on_backend_ready = None
        
        logging.info(self.locale_manager.get_string("request_processor.init.processor_created"))

    def set_readiness_callbacks(self, ui_cb, backend_cb):
        self.on_ui_ready = ui_cb
        self.on_backend_ready = backend_cb

    def process_queues(self, sumo_conn: Any, is_ai_healthy: bool):
        # IMPORTANT CHANGE: Do not abort if sumo_conn is None.
        # In HFT (CentralController) mode, sumo_conn is None, but we need to process
        # Pipe messages (like update_maturity_state) that do not depend on SUMO.
        
        self._process_ui_commands(sumo_conn)

        if is_ai_healthy:
            self._process_ai_requests(sumo_conn)
            try:
                while True: self.watchdog_q.get_nowait()
            except Empty:
                pass
        else:
            if sumo_conn: # Watchdog generally requires SUMO action
                self._process_watchdog_commands(sumo_conn)

    def _process_ui_commands(self, sumo_conn: Any):
        lm = self.locale_manager
        try:
            while True:
                command = self.ui_command_queue.get_nowait()
                if not isinstance(command, dict): continue

                cmd_type = command.get("type")
                payload = command.get("payload", {})

                logging.info(lm.get_string("request_processor.ui_command.received", type=cmd_type))

                if cmd_type == "save_settings":
                    settings_manager = SettingsManager()
                    settings_manager.save_settings(payload)
                    logging.info(lm.get_string("request_processor.ui_command.save_success"))

                elif cmd_type == "set_global_mode":
                    new_mode = payload.get("mode", "AUTOMATIC").upper()
                    old_mode = self.failsafe_manager.current_operation_mode
                    if new_mode != old_mode and new_mode in ["AUTOMATIC", "SEMI_AUTOMATIC", "MANUAL"]:
                        logging.info(f"[CONTROLE GLOBAL] Modo de operação alterado de '{old_mode}' para '{new_mode}' pelo operador.")
                        self.failsafe_manager.current_operation_mode = new_mode
                    elif new_mode != old_mode:
                         logging.warning(f"[RequestProcessor] Tentativa de definir modo global inválido: '{new_mode}'")

                elif cmd_type == "set_semaphore_override":
                    if sumo_conn:
                        self.override_commands_buffer.append(payload)
                        logging.warning(
                            lm.get_string(
                                "request_processor.override.manual_intervention",
                                semaphore_id=payload.get('semaphore_id', 'N/A'),
                                state=payload.get('state', 'N/A')
                            )
                        )
                        self.override_manager.handle_ui_command(payload, sumo_conn)
                    else:
                        logging.warning("[RequestProcessor] Comando de override recebido mas sem conexão SUMO direta (Modo HFT?). Comando ignorado.")

                elif cmd_type == "set_monitor_connection":
                    enabled = payload.get("enabled", False)
                    host = payload.get("host", "localhost")
                    
                    if hasattr(self.failsafe_manager, 'monitor_client') and self.failsafe_manager.monitor_client:
                        if enabled:
                            self.failsafe_manager.monitor_client.connect_manual(host)
                            logging.info(f"[RequestProcessor] Monitor manually CONNECTED to {host}")
                        else:
                            self.failsafe_manager.monitor_client.disconnect_manual()
                            logging.info("[RequestProcessor] Monitor manually DISCONNECTED.")
                    else:
                        logging.warning("[RequestProcessor] MonitorClient interface not found.")
                        
                    # Auto-Save connection intent for the next session
                    settings_manager = SettingsManager()
                    current_settings = settings_manager.load_settings()
                    current_settings["monitor_enabled"] = str(enabled).lower()
                    current_settings["monitor_mqtt_host"] = host
                    settings_manager.save_settings(current_settings)
                    logging.info("[RequestProcessor] Monitor connection state permanently saved to settings.ini.")

                elif cmd_type == "set_semaphore_timings":
                    logging.warning(
                        f"[CONFIGURAÇÃO MANUAL] Operador alterou os tempos do semáforo '{payload.get('semaphore_id', 'N/A')}': "
                        f"Tempo de Verde='{payload.get('green_time', 'N/A')}', Tempo de Amarelo='{payload.get('yellow_time', 'N/A')}' "
                        f"(Modo de Operação: {self.failsafe_manager.current_operation_mode}). (Funcionalidade não implementada no backend)"
                    )
                elif cmd_type == "carina_ready":
                    logging.info("✅ [RequestProcessor] Comando de 'carina_ready' recebido da Interface Gráfica.")
                    if self.on_ui_ready and callable(self.on_ui_ready):
                        self.on_ui_ready()
                else:
                    logging.warning(f"[RequestProcessor] Comando UI desconhecido recebido: {cmd_type}")

        except Empty:
            pass
        except EnvironmentConnectionException as e_conn:
             logging.error(f"[RequestProcessor] Erro de Conexão ao processar comando da UI: {e_conn}", exc_info=True)
        except Exception as e:
            logging.error(lm.get_string("request_processor.ui_command.processing_error", error=e), exc_info=True)

    def _process_ai_requests(self, sumo_conn: Any):
        """
        Processa solicitações vindas do Trainer (IA).
        Gerencia tanto comandos de 4 elementos (padrão) quanto pacotes de dados HFT (2 elementos).
        """
        lm = self.locale_manager
        try:
            if self.ai_pipe_conn.poll():
                request = self.ai_pipe_conn.recv()

                # --- FIX: Handling of HFT/Rich Updates (2-element tuple) ---
                if isinstance(request, tuple) and len(request) == 2:
                    msg_type, payload = request
                    
                    if msg_type == "hft_rich_update":
                        # Update local maturity cache
                        if "maturity" in payload:
                            self.topology_manager.agent_maturity_cache.update(payload["maturity"])
                        
                        # Routes directly to SDS (UI) and SAS (Analysis)
                        try:
                            self.sds_queue.put_nowait(request)
                            self.sas_queue.put_nowait(request)
                        except Full:
                            pass
                            
                        # HFT updates are push data, not commands to TraCI/Override
                        return 
                        
                    elif msg_type == "system" and payload == "backend_ready":
                        logging.info("✅ [RequestProcessor] Comando interno 'backend_ready' recebido da Engine de IA.")
                        if self.on_backend_ready and callable(self.on_backend_ready):
                            self.on_backend_ready()
                        return
                # -------------------------------------------------------------------

                self.health_monitor.record_activity()

                # Standard Commands (4-Element Tuple)
                if self.override_manager.is_ai_command_blocked(request):
                    module_name, func_name, args, _ = request
                    if module_name == 'trafficlight' and func_name == 'setPhase' and args:
                        tl_id = args[0]
                        override_state = self.override_manager.active_overrides.get(tl_id, "N/A")
                        logging.info(
                            lm.get_string(
                                "request_processor.override.ai_ignored",
                                tl_id=tl_id,
                                state=override_state
                            )
                        )
                    self.ai_pipe_conn.send(None)
                    return

                module_name, func_name, args, kwargs = request
                result = None

                if module_name == 'custom':
                    if func_name == 'update_maturity_state':
                        new_phases_data = args[0] if args else {}
                        if isinstance(new_phases_data, dict):
                            self.maturity_phases = new_phases_data
                            
                            # Update HFT Cache
                            real_maturity_map = new_phases_data.get("agent_maturity")
                            if not real_maturity_map:
                                real_maturity_map = {
                                    k: v for k, v in new_phases_data.items() 
                                    if k != "run_id"
                                }
                            if real_maturity_map:
                                self.topology_manager.agent_maturity_cache.update(real_maturity_map)

                            if self.current_run_id is None and isinstance(new_phases_data.get("run_id"), int):
                                 self.current_run_id = new_phases_data.get("run_id")
                                 logging.info(f"[RequestProcessor] Run ID {self.current_run_id} recebido da IA.")
                        result = True

                    elif func_name == 'get_batched_step_data':
                        result = self._collect_batched_step_data(sumo_conn)
                        if result:
                            if self.override_commands_buffer:
                                result["override_commands"] = self.override_commands_buffer.copy()
                                self.override_commands_buffer.clear()
                            try:
                                self.sds_queue.put_nowait(result)
                                self.sas_queue.put_nowait(result)
                            except Full:
                                pass

                else:
                    if sumo_conn is None:
                         pass 
                    else:
                        result = AttributeError(f"Módulo ou Função desconhecida requisitada pela IA: '{module_name}.{func_name}'")
                        logging.error(str(result))

                self.ai_pipe_conn.send(result)

        except EOFError:
             logging.warning("[RequestProcessor] Pipe de comunicação com a IA fechado.")
        except OSError as e_os:
             logging.error(f"[RequestProcessor] Erro de OS no Pipe da IA: {e_os}", exc_info=True)
        except EnvironmentConnectionException as e_conn:
             logging.error(f"[RequestProcessor] Erro de Conexão com Ambiente: {e_conn}", exc_info=True)
             if self.ai_pipe_conn and not self.ai_pipe_conn.closed:
                 self.ai_pipe_conn.send(e_conn)
        except Exception as e:
            logging.error(lm.get_string("request_processor.ai_request.processing_error", error=e), exc_info=True)
            if self.ai_pipe_conn and not self.ai_pipe_conn.closed:
                try:
                    self.ai_pipe_conn.send(e)
                except Exception:
                    pass

    def _process_watchdog_commands(self, sumo_conn: Any):
        lm = self.locale_manager
        command_batch = None
        try:
            while True: command_batch = self.watchdog_q.get_nowait()
        except Empty:
            pass

        if not command_batch: return

        try:
            for command in command_batch:
                cmd_type = command.get("type")
                if cmd_type == "set_program_all":
                    program_id = command.get("value", "0")
                    # No longer iterating sumo_conn.trafficlight directly since we are agnostic.
                    # Environment adapter should ingest 'set_program_all' as a dict-command if required.
                    logging.warning(f"[RequestProcessor] Comando Watchdog '{cmd_type}' interceptado. Adaptação Agnóstica requisitada.")
        except Exception as e:
            logging.error(lm.get_string("request_processor.watchdog.processing_error", error=e), exc_info=True)