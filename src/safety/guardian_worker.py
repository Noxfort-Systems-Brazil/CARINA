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

# File: src/safety/guardian_worker.py (FIXED)
# Author: Gabriel Moraes
# Date: October 5, 2025

"""
Define a lógica para o processo do Guardião Assíncrono.

Esta versão contém o loop de operação principal do worker, que consome
estados da simulação de uma fila, executa a inferência do GuardianAgent
e envia sinais de veto de volta para o processo principal.
"""
import logging
import time
import os
import sys
from multiprocessing import Queue
from queue import Empty
import configparser

def run_guardian_worker(
    settings: configparser.ConfigParser,
    state_queue: Queue,
    signal_queue: Queue,
    scenario_checkpoint_dir: str,
    agent_ids: list
):
    """
    O ponto de entrada e loop principal para o processo do Guardião Assíncrono.
    """
    # Add 'src' directory to path to allow relative imports
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    src_path = os.path.join(project_root, 'src')
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    from utils.logging_setup import setup_logging
    from agents.guardian_agent import GuardianAgent
    # --- FIX 1: Import the LocaleManagerBackend ---
    from utils.locale_manager_backend import LocaleManagerBackend

    # Configure a specific logger for this process
    from src.utils.paths import get_base_output_dir
    log_dir = os.path.join(get_base_output_dir(), "logs", "guardian_worker")
    os.makedirs(log_dir, exist_ok=True)
    setup_logging(log_dir)

    logging.info("[GUARDIAN_WORKER] Processo do Guardião Assíncrono iniciado.")

    # --- FIX 2: Create the LocaleManagerBackend instance ---
    lm = LocaleManagerBackend()

    # --- Initialization ---
    guardians = {}
    guardian_config = settings['GUARDIAN_AGENT']
    for tl_id in agent_ids:
        # In the future, we may add checkpoint loading here if necessary
        # --- FIX 3: Pass locale_manager to constructor ---
        guardians[tl_id] = GuardianAgent(aiconfig=guardian_config, locale_manager=lm)
    
    logging.info(f"[GUARDIAN_WORKER] {len(guardians)} guardiões criados e prontos.")
    
    # --- Main Loop ---
    while True:
        try:
            latest_state_package = None
            
            # 1. Empties the queue to only get the most recent state
            try:
                while True:
                    latest_state_package = state_queue.get_nowait()
            except Empty:
                pass # Queue is empty, normal.

            # 2. If a status has been received, process it
            if latest_state_package:
                # The package contains the status and rewards
                global_state, rewards, done, mode = latest_state_package
                
                for tl_id, guardian in guardians.items():
                    local_state = global_state.get(tl_id)
                    if not local_state:
                        continue
                    
                    # --- Inference and Learning Logic (similar to the old SafetyManager) ---
                    # (This logic will be expanded to use 'soft override')
                    
                    # Guardian Action (Inference)
                    # action = guardian.choose_action(local_state)
                    # if action == 1: # Example: Action 1 means 'veto'
                    # signal_queue.put_nowait({'veto_action': 0, 'target_tl': tl_id})

                    # Guardian Learning (if in training mode)
                    if mode == 'training' and rewards:
                        # The learning logic of the old SafetyManager would be adapted here
                        # guardian.memory.push(...)
                        # guardian.learn()
                        pass

            # Pause to not consume 100% CPU if there is no work
            time.sleep(0.05) 

        except (KeyboardInterrupt, SystemExit):
            logging.info("[GUARDIAN_WORKER] Sinal de encerramento recebido.")
            break
        except Exception as e:
            logging.error(f"[GUARDIAN_WORKER] Erro fatal no loop: {e}", exc_info=True)
            time.sleep(1)
    
    logging.info("[GUARDIAN_WORKER] Processo finalizado.")