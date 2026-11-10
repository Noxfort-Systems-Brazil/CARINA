# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest

from core.enums import Maturity
from maturity.agent_maturity import AgentMaturity


def test_agent_maturity_init_defaults():
    agent = AgentMaturity(agent_id="TL_101")
    assert agent.agent_id == "TL_101"
    assert agent.phase == Maturity.CHILD
    assert agent.episodes_in_phase == 0
    assert len(agent.recent_rewards) == 0
    assert agent.reward_window_size == 10


def test_agent_maturity_invalid_init():
    with pytest.raises(ValueError, match="agent_id cannot be empty"):
        AgentMaturity(agent_id="")

    with pytest.raises(ValueError, match="reward_window_size must be at least 1"):
        AgentMaturity(agent_id="TL_1", reward_window_size=0)


def test_agent_maturity_record_episode():
    agent = AgentMaturity(agent_id="TL_1", reward_window_size=3)

    agent.record_episode(10.5)
    assert agent.episodes_in_phase == 1
    assert list(agent.recent_rewards) == [10.5]

    agent.record_episode(20.0)
    agent.record_episode(30.0)
    assert agent.episodes_in_phase == 3
    assert list(agent.recent_rewards) == [10.5, 20.0, 30.0]

    # Maxlen overflow slides window
    agent.record_episode(40.0)
    assert agent.episodes_in_phase == 4
    assert list(agent.recent_rewards) == [20.0, 30.0, 40.0]


def test_agent_maturity_promote():
    agent = AgentMaturity(agent_id="TL_1")
    agent.record_episode(5.0)
    agent.record_episode(10.0)
    assert agent.episodes_in_phase == 2

    agent.promote(Maturity.TEEN)
    assert agent.phase == Maturity.TEEN
    assert agent.episodes_in_phase == 0
    # Reward history is preserved across transitions
    assert list(agent.recent_rewards) == [5.0, 10.0]


def test_agent_maturity_reset_phase_episodes():
    agent = AgentMaturity(agent_id="TL_1")
    agent.record_episode(1.0)
    assert agent.episodes_in_phase == 1
    agent.reset_phase_episodes()
    assert agent.episodes_in_phase == 0


def test_agent_maturity_resize_reward_window():
    agent = AgentMaturity(agent_id="TL_1", reward_window_size=5)
    for r in [1.0, 2.0, 3.0, 4.0, 5.0]:
        agent.record_episode(r)

    agent.resize_reward_window(2)
    assert agent.reward_window_size == 2
    assert list(agent.recent_rewards) == [4.0, 5.0]

    with pytest.raises(ValueError):
        agent.resize_reward_window(0)


def test_agent_maturity_state_roundtrip():
    agent = AgentMaturity(agent_id="TL_99", phase=Maturity.TEEN, episodes_in_phase=12, recent_rewards=[1.5, 2.5])
    state_tuple = agent.to_state_tuple()
    assert state_tuple == ("TL_99", "TEEN", 12, [1.5, 2.5])

    restored = AgentMaturity.from_state(
        agent_id=state_tuple[0],
        phase_name=state_tuple[1],
        episodes_in_phase=state_tuple[2],
        recent_rewards=state_tuple[3],
        reward_window_size=10,
    )
    assert restored.agent_id == "TL_99"
    assert restored.phase == Maturity.TEEN
    assert restored.episodes_in_phase == 12
    assert list(restored.recent_rewards) == [1.5, 2.5]


def test_agent_maturity_repr():
    agent = AgentMaturity(agent_id="TL_1", phase=Maturity.ADULT, episodes_in_phase=42)
    rep = repr(agent)
    assert "TL_1" in rep
    assert "ADULT" in rep
    assert "42" in rep
