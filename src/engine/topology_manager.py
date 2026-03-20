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

# File: src/engine/topology_manager.py
# Author: Gabriel Moraes
# Date: February 17, 2026

import os
import logging
import sumolib # type: ignore
from typing import Dict, Tuple

from agents.local_agent import LocalAgent
from utils.paths import get_base_output_dir
from core.enums import Maturity

class TopologyManager:
    """
    Gerenciador responsável pelo carregamento da infraestrutura viária e
    pela inicialização (ou reinicialização) da população de agentes.
    """

    def __init__(self, settings, locale_manager, log_dir):
        self.settings = settings
        self.locale_manager = locale_manager
        self.log_dir = log_dir
        
        # AI parameters extracted from settings
        self.n_actions = 3
        self.default_n_observations = self.settings.getint('AI_TRAINING', 'observation_space_size', fallback=80)

    def load_topology(self, map_path: str, state_extractor, maturity_manager) -> Tuple[Dict[str, LocalAgent], Dict[str, int]]:
        """
        Lê o arquivo de rede do SUMO, cria os agentes para cada semáforo encontrado,
        carrega seus cérebros (checkpoints) e restaura seu nível de maturidade.

        Args:
            map_path (str): Caminho absoluto para o arquivo .net.xml.
            state_extractor (StateExtractor): Referência para carregar o mapa de vizinhança estrutural.
            maturity_manager (MaturityManager): Referência para registrar os novos agentes.

        Returns:
            Tuple[Dict, Dict]: Retorna um dicionário de novos agentes e um dicionário de fases iniciais.
        """
        agents: Dict[str, LocalAgent] = {}
        initial_phases: Dict[str, int] = {}

        logging.info(f"[TOPOLOGY] Construindo mapa de vizinhança ESTRUTURAL a partir de: {map_path}")
        
        # 1. Update StateExtractor with the new topology
        state_extractor.load_topology(map_path)
        
        try:
            # 2. Network Reading via Sumolib
            net = sumolib.net.readNet(map_path, withInternal=False)
            tls_list = net.getTrafficLights()
            
            logging.info(f"[TOPOLOGY] Rede carregada. Encontrados {len(tls_list)} semáforos controláveis.")
            
            # Base path for checkpoints
            checkpoints_dir = os.path.join(get_base_output_dir(), "results", "hft_live_session", "checkpoints")

            # 3. Instantiation of Agents
            for tls in tls_list:
                tl_id = tls.getID()
                initial_phases[tl_id] = 0
                
                # Determine observation space size dynamically if possible
                obs_size = state_extractor.get_observation_space_size(tl_id)
                if obs_size == 0:
                    obs_size = self.default_n_observations
                
                # Agent Creation
                new_agent = LocalAgent(
                    tlight_id=tl_id,
                    n_observations=obs_size,
                    n_actions=self.n_actions,
                    initial_hyperparams={},
                    log_dir=self.log_dir,
                    locale_manager=self.locale_manager
                )
                
                # 4. Checkpoint and Maturity Smart Charging
                ckpt_path = os.path.join(checkpoints_dir, f"agent_{tl_id}.pth")
                saved_maturity_stage = "CHILD" # Default value if it is a new agent

                if os.path.exists(ckpt_path):
                    logging.info(f"[TOPOLOGY] Carregando cérebro existente para o agente {tl_id}...")
                    # Now we capture the returned phase (ex: "TEEN")
                    saved_maturity_stage = new_agent.load_checkpoint(ckpt_path)
                else:
                    logging.info(f"[TOPOLOGY] Nenhum checkpoint encontrado para {tl_id}. Criando novo cérebro.")
                    self._create_initial_checkpoint(tl_id, new_agent)

                agents[tl_id] = new_agent
                
                # 5. Registration and State Restoration
                # First registers (which sets to CHILD by default if it doesn't exist)
                maturity_manager.register_agents([tl_id])
                
                # If the checkpoint indicated an advanced phase, we update the manager manually
                if saved_maturity_stage != "CHILD" and saved_maturity_stage in Maturity.__members__:
                    restored_enum = Maturity[saved_maturity_stage]
                    maturity_manager.agent_maturity[tl_id] = restored_enum
                    logging.info(f"[TOPOLOGY] Maturidade de {tl_id} restaurada para {saved_maturity_stage}")

            logging.info(f"[TOPOLOGY] População com {len(agents)} agentes inicializada e sincronizada.")
            
        except Exception as e:
            logging.error(f"[TOPOLOGY] Erro crítico ao carregar topologia: {e}", exc_info=True)
            raise e

        return agents, initial_phases

    def _create_initial_checkpoint(self, tl_id: str, agent: LocalAgent):
        """Salva o estado inicial do agente no disco apenas se não existir."""
        try:
            ckpt_path = os.path.join(
                get_base_output_dir(), 
                "results", "hft_live_session", "checkpoints", 
                f"agent_{tl_id}.pth"
            )
            os.makedirs(os.path.dirname(ckpt_path), exist_ok=True)
            # Saves as CHILD explicitly
            agent.save_checkpoint(ckpt_path, maturity_stage="CHILD")
            logging.debug(f"[TOPOLOGY] Checkpoint inicial criado para {tl_id}")
        except Exception as e:
            logging.error(f"[TOPOLOGY] Falha ao criar checkpoint físico para {tl_id}: {e}")