# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Backwards-compatible re-export facade for modularized local-agent collaborators.
Concrete implementations live under `src/agents/`:
  - `pae_state_augmentor.PAEStateAugmentor`
  - `agent_hyperparameter_manager.AgentHyperparameterManager`
  - `checkpoint_migrator.CheckpointMigrator`
  - `agent_checkpoint_manager.AgentCheckpointManager`
"""

try:
    from src.agents.agent_checkpoint_manager import AgentCheckpointManager
    from src.agents.agent_hyperparameter_manager import AgentHyperparameterManager
    from src.agents.checkpoint_migrator import CheckpointMigrator
    from src.agents.pae_state_augmentor import PAEStateAugmentor
except ImportError:
    from agents.agent_checkpoint_manager import AgentCheckpointManager
    from agents.agent_hyperparameter_manager import AgentHyperparameterManager
    from agents.checkpoint_migrator import CheckpointMigrator
    from agents.pae_state_augmentor import PAEStateAugmentor

__all__ = [
    "PAEStateAugmentor",
    "AgentHyperparameterManager",
    "CheckpointMigrator",
    "AgentCheckpointManager",
]
