# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Maturity State Serializer (Domain / Application Layer / SOLID: SRP).
Encapsulates state packing, unpacking, persistence, and loading for traffic light agent maturity.
"""

import logging
from typing import Any, Dict, Optional

from core.enums import Maturity
from maturity.agent_maturity import AgentMaturity


class MaturityStateSerializer:
    """Handles serialization, saving, and loading of AgentMaturity entity states."""

    @staticmethod
    def get_state(agents: Dict[str, AgentMaturity]) -> dict:
        """Serializes current in-memory agent maturities into a primitive dict."""
        return {
            "agent_maturity": {aid: agent.phase.name for aid, agent in agents.items()},
            "agent_episodes_in_phase": {aid: agent.episodes_in_phase for aid, agent in agents.items()},
            "agent_recent_rewards": {aid: list(agent.recent_rewards) for aid, agent in agents.items()},
        }

    @classmethod
    def save_state(
        cls,
        repository: Any,
        filepath: str,
        agents: Dict[str, AgentMaturity],
        locale_manager: Optional[Any] = None,
    ) -> bool:
        """Saves current agents state to repository."""
        state = cls.get_state(agents)
        return repository.save(filepath, state, locale_manager)

    @classmethod
    def load_state(
        cls,
        repository: Any,
        filepath: str,
        reward_window_size: int,
        locale_manager: Optional[Any] = None,
    ) -> Dict[str, AgentMaturity]:
        """Loads and reconstructs AgentMaturity entities from repository."""
        state = repository.load(filepath, locale_manager)
        restored_agents: Dict[str, AgentMaturity] = {}
        if not state:
            return restored_agents

        try:
            raw_maturity = state.get("agent_maturity", {})
            raw_episodes = state.get("agent_episodes_in_phase", {})
            raw_rewards = state.get("agent_recent_rewards", {})
            for aid, maturity_name in raw_maturity.items():
                restored_agents[aid] = AgentMaturity.from_state(
                    agent_id=aid,
                    phase_name=maturity_name,
                    episodes_in_phase=raw_episodes.get(aid, 0),
                    recent_rewards=raw_rewards.get(aid, []),
                    reward_window_size=reward_window_size,
                )
        except (KeyError, ValueError) as e:
            if locale_manager:
                logging.error(locale_manager.get_string("maturity_manager.load.error", error=e), exc_info=True)
            else:
                logging.error(f"[MaturityStateSerializer] Error loading state: {e}", exc_info=True)

        return restored_agents
