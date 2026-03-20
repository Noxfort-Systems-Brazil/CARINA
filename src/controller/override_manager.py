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

# File: src/controller/override_manager.py (Refactored with robust TraCIException import)
# Author: Gabriel Moraes
# Date: October 26, 2025

import logging
import os
import sys # Import sys for path manipulation
import json
from typing import Dict, Tuple, TYPE_CHECKING

# Add 'src' directory to path (kept)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

if TYPE_CHECKING:
    # Assume LocaleManagerBackend is in src/utils
    from utils.locale_manager_backend import LocaleManagerBackend

class EnvironmentConnectionException(Exception):
    pass

class OverrideManager:
    """
    Um especialista que gerencia o estado e a execução de overrides manuais
    nos semáforos, persistindo o seu estado em disco.
    """
    def __init__(self, locale_manager: 'LocaleManagerBackend'): # Fixed type hint
        self.locale_manager = locale_manager
        self.active_overrides: Dict[str, str] = {}
        self.state_file_path: str | None = None
        logging.info("Gerenciador de Overrides Manuais criado.")

    def init_persistence(self, scenario_name: str):
        """
        Define o caminho do arquivo de estado e carrega o estado anterior.
        """
        if not scenario_name:
            logging.error("[OverrideManager] Nome do cenário não fornecido. A persistência de override está desativada.")
            return

        # Recalculate project_root here too to ensure
        from src.utils.paths import get_base_output_dir
        scenario_dir = os.path.join(get_base_output_dir(), "results", scenario_name)
        os.makedirs(scenario_dir, exist_ok=True)
        self.state_file_path = os.path.join(scenario_dir, "override_state.json")
        self._load_state_from_disk()

    def _load_state_from_disk(self):
        """Lê o arquivo JSON de estado, se ele existir."""
        if self.state_file_path and os.path.exists(self.state_file_path):
            try:
                with open(self.state_file_path, "r", encoding="utf-8") as f:
                    self.active_overrides = json.load(f)
                logging.info(f"Estado de override carregado de {self.state_file_path}. {len(self.active_overrides)} semáforos em modo manual.")
            except (IOError, json.JSONDecodeError) as e:
                logging.error(f"Erro ao carregar o estado de override: {e}")

    def _save_state_to_disk(self):
        """Salva o dicionário de overrides ativos no arquivo JSON."""
        if not self.state_file_path:
            logging.warning("[OverrideManager] Tentativa de salvar o estado de override antes da inicialização completa. Ignorando.")
            return
        try:
            with open(self.state_file_path, "w", encoding="utf-8") as f:
                json.dump(self.active_overrides, f, indent=4)
        except IOError as e:
            logging.error(f"Erro ao salvar o estado de override: {e}")

    def restore_sumo_state(self, sumo_conn):
        """
        Aplica os estados de override carregados na simulação do SUMO.
        """
        if not self.active_overrides or not sumo_conn: # Add sumo_conn check
            return

        logging.info("Restaurando estados de override manuais na simulação do SUMO...")
        for semaphore_id, state in self.active_overrides.items():
            payload = {"semaphore_id": semaphore_id, "state": state}
            # Calls handle_ui_command which already has the try/except TraCIException
            self.handle_ui_command(payload, sumo_conn, is_restoring=True)

    def handle_ui_command(self, payload: Dict, sumo_conn, is_restoring: bool = False):
        """
        Processa um comando de override vindo da UI e o aplica no SUMO.
        """
        semaphore_id = payload.get("semaphore_id")
        state = payload.get("state")

        if not semaphore_id or not state or not sumo_conn: # Add sumo_conn check
            logging.warning(f"[OverrideManager] Comando UI inválido ou conexão SUMO ausente. Payload: {payload}")
            return

        try:
            # Checks if the traffic light exists in the simulation before trying to control it
            # (May be useful if the state is loaded from a different scenario)
            all_tls_ids = sumo_conn.trafficlight.getIDList()
            if semaphore_id not in all_tls_ids:
                 logging.warning(f"[OverrideManager] Tentativa de override no semáforo '{semaphore_id}' que não existe na simulação atual. Ignorando.")
                 # Removes from active state if no longer exists
                 if semaphore_id in self.active_overrides:
                     del self.active_overrides[semaphore_id]
                     if not is_restoring: self._save_state_to_disk()
                 return

            if state == "ALERT":
                self.active_overrides[semaphore_id] = state
                if not is_restoring: logging.info(f"[Agnostic] Semáforo '{semaphore_id}' comandado para estado de Alerta.")

            elif state == "OFF":
                self.active_overrides[semaphore_id] = state
                if not is_restoring: logging.info(f"[Agnostic] Semáforo '{semaphore_id}' comandado para estado Desativado.")

            elif state == "NORMAL":
                if semaphore_id in self.active_overrides:
                    del self.active_overrides[semaphore_id]
                if not is_restoring: logging.info(f"[Agnostic] Semáforo '{semaphore_id}' devolvido ao controle automático.")

            if not is_restoring:
                self._save_state_to_disk()

        except Exception as e_general: 
             logging.error(f"Erro inesperado ao aplicar override para '{semaphore_id}': {e_general}", exc_info=True)


    def is_ai_command_blocked(self, request: Tuple) -> bool:
        """Verifica se um comando vindo da IA deve ser bloqueado devido a um override."""
        # The internal logic remains the same
        try:
            module_name, func_name, args, _ = request
            # Only blocks 'setPhase' commands from AI for traffic lights with active override
            if module_name == 'trafficlight' and func_name == 'setPhase' and args:
                tl_id = args[0]
                if tl_id in self.active_overrides:
                    # Skipped action log is handled in request_processor
                    return True
        except (IndexError, TypeError, ValueError) as e:
             # Error unpacking the request - logs in and considers it not blocked for security
             logging.warning(f"[OverrideManager] Erro ao analisar requisição da IA para bloqueio: {e}. Requisição: {request}")
        return False