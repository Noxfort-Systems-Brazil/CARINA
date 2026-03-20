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

# File: src/core/decision_coordinator.py
# Author: Gabriel Moraes
# Date: 02/18/2026

"""
Define a classe DecisionCoordinator.
Este componente encapsula a lógica de comunicação entre agentes e
a tomada de decisão coordenada a cada passo da simulação.

Atualizado para incluir:
1. Lógica Neuro-Simbólica do Agente Guardião (Vetos).
2. Construção do vetor de estado completo (GAT + Vizinhos + Overrides).
"""

import logging
import torch
from typing import TYPE_CHECKING, Dict

from core.observation_builder import ObservationBuilder
from core.inference_engine import InferenceEngine
from core.safety_auditor import SafetyAuditor

if TYPE_CHECKING:
    from core.strategic_coordinator import StrategicCoordinator
    from engine.environment import SumoEnvironment
    from agents.local_agent import LocalAgent
    from agents.guardian_agent import GuardianAgent # New dependency

try:
    from traci.exceptions import TraCIException
except (ImportError, ModuleNotFoundError):
    import sys, os
    if 'SUMO_HOME' in os.environ:
        tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
        if tools not in sys.path:
            sys.path.append(tools)
        from traci.exceptions import TraCIException
    else:
        logging.warning("SUMO_HOME não definido, a importação de TraCIException pode falhar.")
        TraCIException = Exception

class DecisionCoordinator:
    def __init__(self, agents: Dict[str, 'LocalAgent'], 
                 neighborhoods: dict, 
                 environment: 'SumoEnvironment', 
                 strategic_coordinator: 'StrategicCoordinator',
                 guardian_agent: 'GuardianAgent', # Guardian's Injection
                 message_size: int,
                 n_observations: int):
        """
        Inicializa o Coordenador de Decisões.
        """
        self.agents = agents
        self.neighborhoods = neighborhoods
        self.env = environment
        self.strategic_coordinator = strategic_coordinator
        self.guardian = guardian_agent # Stores the Guardian
        self.message_size = message_size
        self.n_observations = n_observations
        
        self.override_states: Dict[str, str] = {} 
        
        self.builder = ObservationBuilder(message_size, n_observations)
        self.engine = InferenceEngine()
        self.auditor = SafetyAuditor(guardian_agent)
        
        logging.info("[COORDINATOR] Coordenador de Decisões (Com Guardião Neuro-Simbólico) criado.")

    def get_coordinated_actions(self, 
                                current_states: dict, 
                                state_history: dict,
                                current_operation_mode: str) -> tuple:
        """
        Executa o ciclo de decisão:
        1. Coleta mensagens (GAT/Vizinhos).
        2. Agente Local sugere ação.
        3. Agente Guardião valida (Veto Neuro-Simbólico).
        4. Retorna ações finais.
        """
        if not current_states:
            return {}, {}

        # --- PHASE 1: Posting Messages ---
        messages = self.builder.gather_messages(current_states, self.env.state_extractor._get_green_phases_for_tl)

        # --- PHASE 2: Coordinated Decision and Supervision ---
        actions_to_apply = {}
        last_decision_data = {}
        vetos_applied = {} # For log/debug

        is_manual_mode = current_operation_mode == "MANUAL"

        for tl_id, agent in self.agents.items():
            local_state = current_states.get(tl_id)
            if not local_state or not isinstance(local_state, list):
                continue

            gat_vector = self.strategic_coordinator.get_strategic_vector_for_agent(tl_id)
            override_state = self.override_states.get(tl_id)

            augmented_state = self.builder.build_state(
                tl_id, local_state, messages, self.neighborhoods, 
                gat_vector, override_state, is_manual_mode
            )

            if tl_id not in state_history:
                 continue

            state_history[tl_id].append(augmented_state)
            state_sequence = list(state_history[tl_id])

            try:
                # 1. Local Agent suggests the action
                suggested_action, action_tensor, log_prob, state_val, dist_entropy = self.engine.predict(agent, state_sequence)

                # 2. Guardian Audits the Decision
                final_action, was_vetoed = self.auditor.audit(suggested_action, tl_id, augmented_state, self.env)
                
                if was_vetoed:
                    vetos_applied[tl_id] = "Safety Veto"

                # Record the final action
                actions_to_apply[tl_id] = final_action

                last_decision_data[tl_id] = {
                    'state_sequence': state_sequence,
                    'action': action_tensor, # Saves the original tensioner for PPO training
                    'log_prob': log_prob,
                    'state_val': state_val,
                    'entropy': dist_entropy.item(),
                    'vetoed': tl_id in vetos_applied
                }

            except Exception as e_action:
                 logging.error(f"[Coordinator] Erro na decisão para {tl_id}: {e_action}", exc_info=True)

        return actions_to_apply, last_decision_data

        return actions_to_apply, last_decision_data