# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from collections import deque
from typing import List, Optional

from core.enums import Maturity


class AgentMaturity:
    """
    Rich Domain Entity representing the maturity lifecycle and recent performance
    history of an autonomous traffic light agent.
    """

    def __init__(
        self,
        agent_id: str,
        phase: Maturity = Maturity.CHILD,
        episodes_in_phase: int = 0,
        recent_rewards: Optional[List[float]] = None,
        reward_window_size: int = 10,
    ) -> None:
        if not agent_id:
            raise ValueError("agent_id cannot be empty.")
        if reward_window_size < 1:
            raise ValueError("reward_window_size must be at least 1.")

        self.agent_id = str(agent_id)
        self.phase = phase
        self.episodes_in_phase = max(0, int(episodes_in_phase))
        self.reward_window_size = int(reward_window_size)
        self.recent_rewards: deque = deque(
            recent_rewards if recent_rewards is not None else [],
            maxlen=self.reward_window_size,
        )

    def record_episode(self, reward: float) -> None:
        """
        Records the completion of an episode for this agent.
        Increments episodes spent in the current phase and tracks the reward.
        """
        self.episodes_in_phase += 1
        self.recent_rewards.append(float(reward))

    def promote(self, new_phase: Maturity) -> None:
        """
        Transitions the agent to a new maturity phase, resetting the in-phase episode counter.
        """
        self.phase = new_phase
        self.episodes_in_phase = 0

    def reset_phase_episodes(self) -> None:
        """Resets the episode counter for the current phase without changing phase."""
        self.episodes_in_phase = 0

    def resize_reward_window(self, new_window_size: int) -> None:
        """Resizes the internal reward window deque while preserving recent entries."""
        if new_window_size < 1:
            raise ValueError("new_window_size must be at least 1.")
        self.reward_window_size = int(new_window_size)
        self.recent_rewards = deque(list(self.recent_rewards), maxlen=self.reward_window_size)

    def to_state_tuple(self) -> tuple:
        """Returns (agent_id, phase_name, episodes_in_phase, recent_rewards_list)."""
        return (
            self.agent_id,
            self.phase.name,
            self.episodes_in_phase,
            list(self.recent_rewards),
        )

    @classmethod
    def from_state(
        cls,
        agent_id: str,
        phase_name: str,
        episodes_in_phase: int = 0,
        recent_rewards: Optional[List[float]] = None,
        reward_window_size: int = 10,
    ) -> "AgentMaturity":
        """Factory method to reconstitute an AgentMaturity entity from stored state."""
        phase = Maturity[phase_name] if phase_name in Maturity.__members__ else Maturity.CHILD
        return cls(
            agent_id=agent_id,
            phase=phase,
            episodes_in_phase=episodes_in_phase,
            recent_rewards=recent_rewards,
            reward_window_size=reward_window_size,
        )

    def __repr__(self) -> str:
        return (
            f"AgentMaturity(agent_id='{self.agent_id}', phase={self.phase.name}, "
            f"episodes={self.episodes_in_phase}, window_size={self.reward_window_size})"
        )
