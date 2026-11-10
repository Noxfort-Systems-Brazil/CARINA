# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Defines the OnPolicyBuffer class.

This class, extracted from 'local_agent.py', implements a simple memory buffer,
designed for "on-policy" reinforcement learning algorithms like PPO. It collects
a batch of transitions and converts them into PyTorch tensors for the learning cycle.
"""
import numpy as np
import torch


class OnPolicyBuffer:
    """A buffer that stores transitions (state, action, etc.) for a single data collection cycle."""

    def __init__(self):
        """Initializes the lists that will store the trajectory data."""
        self.actions = []
        self.states = []
        self.log_probs = []
        self.rewards = []
        self.dones = []
        self.state_values = []

    def push(self, state_sequence, action, log_prob, reward, done, state_value):
        """
        Adds a single transition to the buffer.

        Args:
            state_sequence: State sequence that led to the decision.
            action: Action taken by the agent.
            log_prob: Log probability of the action taken.
            reward (float): Reward received after the action.
            done (bool): Whether the episode terminated after the action.
            state_value: State value estimated by the Critic.
        """
        self.states.append(state_sequence)
        self.actions.append(action)
        self.log_probs.append(log_prob)
        self.rewards.append(reward)
        self.dones.append(done)
        self.state_values.append(state_value)

    def get_batch(self) -> tuple:
        """
        Converts stored data to PyTorch tensors and returns them.
        Assumes state sequences already have uniform shape.

        Returns:
            tuple: A tuple containing state tensors, actions, log_probs,
                   rewards (list), dones (list), and state values.
        """
        # Converting to numpy array first is efficient
        states_np = np.array(self.states, dtype=np.float32)
        actions_np = np.array(self.actions, dtype=np.float32)
        log_probs_np = np.array(self.log_probs, dtype=np.float32)
        state_values_np = np.array(self.state_values, dtype=np.float32)

        # Converts to PyTorch tensors
        states_t = torch.from_numpy(states_np)
        actions_t = torch.from_numpy(actions_np)
        log_probs_t = torch.from_numpy(log_probs_np)
        state_values_t = torch.from_numpy(state_values_np)

        # The squeeze() method removes dimensions of size 1, if any
        return states_t, actions_t.squeeze(), log_probs_t.squeeze(), self.rewards, self.dones, state_values_t.squeeze()

    def clear(self):
        """Clears the buffer. Must be called after each learning cycle."""
        self.actions = []
        self.states = []
        self.log_probs = []
        self.rewards = []
        self.dones = []
        self.state_values = []

    def __len__(self) -> int:
        """Returns the number of transitions stored in the buffer."""
        return len(self.states)
