import logging
from collections import deque
from typing import Dict

class StateHistoryManager:
    """
    Manages the rolling Deque buffers that form the observation horizon for Agents.
    """

    def __init__(self, sequence_length: int, n_observations: int):
        if sequence_length <= 0:
            logging.warning("[StateHistoryManager] 'sequence_length' must be > 0. Using 1.")
            self.sequence_length = 1
        else:
            self.sequence_length = sequence_length
            
        self.n_observations = n_observations
        self.history: Dict[str, deque] = {}

    def initialize_history(self, initial_states: dict, agent_ids: list):
        if not initial_states or not agent_ids:
            logging.warning("[StateHistoryManager] Initial states or agents missing.")
            return

        if self.n_observations <= 0:
            logging.error(f"[StateHistoryManager] Observation size invalid ({self.n_observations}). History not initialized.")
            return

        self.history.clear()

        for tl_id in agent_ids:
            history_deque = deque(maxlen=self.sequence_length)
            zero_state = [0.0] * self.n_observations
            
            for _ in range(self.sequence_length):
                history_deque.append(zero_state)
                
            self.history[tl_id] = history_deque

        logging.debug(f"[StateHistoryManager] Initialized history for {len(self.history)} agents.")
