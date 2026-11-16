# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""PPO hyperparameter loading and live network/optimizer propagation for local agents."""

from typing import TYPE_CHECKING, Any, Dict

import torch.nn as nn

if TYPE_CHECKING:
    from src.agents.local_agent import LocalAgent


class AgentHyperparameterManager:
    """Manages hyperparameters and applies them to networks and optimizers."""

    @staticmethod
    def load(agent: "LocalAgent") -> None:
        agent.gamma = float(agent.hyperparams.get("gamma", 0.99))
        agent.gae_lambda = float(agent.hyperparams.get("gae_lambda", 0.95))
        agent.learning_rate = float(agent.hyperparams.get("learning_rate", 0.0001))
        agent.eps_clip = float(agent.hyperparams.get("eps_clip", 0.2))
        agent.k_epochs = int(agent.hyperparams.get("k_epochs", 4))
        agent.target_kl = float(agent.hyperparams.get("target_kl", 0.02))
        agent.grad_clip_norm = float(agent.hyperparams.get("grad_clip_norm", 0.5))
        agent.dropout_p = float(agent.hyperparams.get("dropout_p", 0.1))
        agent.critic_loss_coef = float(agent.hyperparams.get("critic_loss_coef", 0.5))

    @staticmethod
    def update(agent: "LocalAgent", new_hyperparams: Dict[str, Any]) -> None:
        agent.hyperparams = new_hyperparams
        AgentHyperparameterManager.load(agent)
        if agent.optimizer:
            agent.optimizer.param_groups[0]["lr"] = agent.learning_rate
        if agent.policy_net and hasattr(agent.policy_net, "modules"):
            for module in agent.policy_net.modules():
                try:
                    if isinstance(module, nn.Dropout):
                        module.p = agent.dropout_p
                except TypeError:
                    pass
