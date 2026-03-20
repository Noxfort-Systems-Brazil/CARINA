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

# File: src/agents/guardian_agent.py
# Author: Gabriel Moraes
# Date: 02/18/2026

import torch
import torch.nn as nn
import torch.optim as optim
import random
import logging
from typing import TYPE_CHECKING, Optional, Dict, Any

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

from models.dueling_dqn import DuelingDQN
from memory.replay_memory import ReplayMemory, Transition

class GuardianAgent:
    """
    The Neuro-Symbolic Guardian Agent (Configurable).
    
    It combines a Dueling DQN (Neural) with dynamic Safety Rules (Symbolic) 
    loaded from settings.ini. It acts as a safety shield, vetoing 
    actions that violate engineering constraints (Min Green, Ghost Green).
    """
    
    # Action Constants
    ACTION_KEEP_PHASE = 0
    ACTION_CHANGE_PHASE = 1

    def __init__(self, aiconfig, traffic_rules_config, locale_manager: 'LocaleManagerBackend'):
        """
        Args:
            aiconfig: Configuration section for AI hyperparameters.
            traffic_rules_config: Configuration section [TRAFFIC_RULES] from settings.ini.
            locale_manager: Backend locale manager.
        """
        self.locale_manager = locale_manager
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._load_hyperparameters(aiconfig)
        
        # --- Configurable Safety Rules (Symbolic Layer) ---
        # Reads from settings.ini [TRAFFIC_RULES]
        self.min_green_time = traffic_rules_config.getfloat('min_green_time_seconds', fallback=15.0)
        self.yellow_time = traffic_rules_config.getfloat('yellow_time_seconds', fallback=4.0)
        self.all_red_time = traffic_rules_config.getfloat('all_red_time_seconds', fallback=2.0)
        
        logging.info(f"[GUARDIAN] Initialized with Safety Rules -> Min Green: {self.min_green_time}s | Yellow: {self.yellow_time}s | All-Red: {self.all_red_time}s")

        # --- Neural Layer (The Intuition) ---
        self.policy_net = DuelingDQN().to(self.device)
        self.target_net = DuelingDQN().to(self.device)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()
        
        self.optimizer = optim.AdamW(self.policy_net.parameters(), lr=self.learning_rate)
        self.memory = ReplayMemory(self.memory_size)
        
        self.steps_done = 0
        self.scaler = torch.amp.GradScaler(enabled=(self.device.type == 'cuda'))
        
        logging.info(self.locale_manager.get_string("guardian_agent.init.success", enabled=self.scaler.is_enabled()))

    def _load_hyperparameters(self, cfg):
        """Loads hyperparameters from configuration."""
        self.batch_size = cfg.getint('batch_size', 128)
        self.gamma = cfg.getfloat('gamma', 0.90)
        self.epsilon_start = cfg.getfloat('epsilon_start', 1.0)
        self.epsilon_end = cfg.getfloat('epsilon_end', 0.05)
        self.epsilon_decay = cfg.getint('epsilon_decay', 30000)
        self.learning_rate = cfg.getfloat('learning_rate', 0.00025)
        self.memory_size = cfg.getint('memory_size', 50000)

    def select_action(self, state: list, context: Dict[str, Any]) -> int:
        """
        The core decision method of the Neuro-Symbolic architecture.
        """
        
        # --- STEP 1: SYMBOLIC BARRIER (Configurable Rules) ---
        # Extract context data
        current_phase_duration = context.get('current_phase_duration', 0.0)
        next_phase_has_flow = context.get('next_phase_has_flow', True)
        
        # Rule 1: Minimum Green Time Violation
        if current_phase_duration < self.min_green_time:
            # Logging commented out to avoid spam, uncomment for debugging
            # logging.debug(f"[SAFETY VETO] Min Green Violation. Elapsed: {current_phase_duration:.1f}s < {self.min_green_time}s")
            return self.ACTION_KEEP_PHASE

        # Rule 2: No Flow / Empty Road (Ghost Green)
        if not next_phase_has_flow:
            # logging.debug("[SAFETY VETO] No Flow detected on target phase. Keeping current phase.")
            return self.ACTION_KEEP_PHASE

        # --- STEP 3: ALL-RED AWARENESS (Implicit) ---
        # Note: All-Red time (2s) is handled by the Actuator/CycleManager during the transition state.
        # The Guardian does not need to enforce it here, but knows it exists for future reward calculation logic.

        # --- STEP 4: NEURAL INFERENCE (Dueling DQN) ---
        # If rules passed, allow Neural Net to decide risk
        
        eps_threshold = self.epsilon_end + (self.epsilon_start - self.epsilon_end) * \
                        (1. - min(1., self.steps_done / self.epsilon_decay))
        self.steps_done += 1
        
        if random.random() > eps_threshold:
            with torch.no_grad():
                state_tensor = torch.tensor(state, dtype=torch.float32, device=self.device).unsqueeze(0)
                # Returns the index of the max q-value (0 or 1)
                neural_action = self.policy_net(state_tensor).max(1)[1].item()
                return neural_action
        else:
            # Random exploration
            return random.randrange(2)

    def learn(self):
        """Executes a specialized optimization step for Dueling DQN."""
        if len(self.memory) < self.batch_size:
            return
            
        transitions = self.memory.sample(self.batch_size)
        batch = Transition(*zip(*transitions))

        non_final_mask = torch.tensor(tuple(map(lambda s: s is not None, batch.next_state)), device=self.device, dtype=torch.bool)
        non_final_next_states = torch.cat([s for s in batch.next_state if s is not None])
        
        state_batch = torch.cat(batch.state)
        action_batch = torch.cat(batch.action)
        reward_batch = torch.cat(batch.reward)

        self.optimizer.zero_grad()
        
        with torch.amp.autocast(device_type=self.device.type, enabled=self.scaler.is_enabled()):
            state_action_values = self.policy_net(state_batch).gather(1, action_batch)
            next_state_values = torch.zeros(self.batch_size, device=self.device)
            with torch.no_grad():
                next_state_values[non_final_mask] = self.target_net(non_final_next_states).max(1)[0].float()
            
            expected_state_action_values = (next_state_values * self.gamma) + reward_batch
            loss = nn.SmoothL1Loss()(state_action_values, expected_state_action_values.unsqueeze(1))

        self.scaler.scale(loss).backward()
        torch.nn.utils.clip_grad_norm_(self.policy_net.parameters(), 1.0)
        self.scaler.step(self.optimizer)
        self.scaler.update()

    def update_target_net(self):
        """Soft update or Hard update of target network weights."""
        self.target_net.load_state_dict(self.policy_net.state_dict())