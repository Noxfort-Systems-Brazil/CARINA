# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional

import numpy as np
import torch
from captum.attr import IntegratedGradients

from agents.local_agent import LocalAgent
from xai.captum_model_wrapper import CaptumModelWrapper


class CaptumAttributionEngine:
    """
    Responsibility: Handle PyTorch and Captum mathematical operations.
    Computes raw feature importances using Integrated Gradients.
    """

    def __init__(self, agent: LocalAgent, device: torch.device) -> None:
        self.agent = agent
        self.device = device
        if hasattr(self.agent.policy_net, "eval"):
            self.agent.policy_net.eval()
        self.wrapped_model = CaptumModelWrapper(
            self.agent.policy_net, shared_pae=getattr(self.agent, "shared_pae", None)
        ).to(self.device)
        if hasattr(self.wrapped_model, "eval"):
            self.wrapped_model.eval()
        self.ig = IntegratedGradients(self.wrapped_model)

    def compute_importances(self, limit: int = 100) -> Optional[np.ndarray]:
        try:
            if self.agent.xai_memory is None or self.agent.xai_memory.size == 0:
                import logging

                logging.info(
                    f"[CaptumAttributionEngine] No tensor data in memory for agent {getattr(self.agent, 'id', 'N/A')}."
                )
                return None

            if hasattr(self.wrapped_model, "eval"):
                self.wrapped_model.eval()

            # Limit the number of samples to avoid excessive CPU compute times (max 100 samples)
            limit = min(self.agent.xai_memory.size, limit)
            if self.agent.xai_memory.size <= limit:
                input_tensors = self.agent.xai_memory.states[: self.agent.xai_memory.size].to(self.device)
            else:
                ptr = self.agent.xai_memory.ptr
                indices = [(ptr - 1 - i) % self.agent.xai_memory.capacity for i in range(limit)]
                indices_t = torch.tensor(indices, device=self.agent.xai_memory.states.device, dtype=torch.long)
                input_tensors = self.agent.xai_memory.states[indices_t].to(self.device)

            baselines = torch.zeros_like(input_tensors)

            # Run Integrated Gradients (n_steps=25 for TCN efficiency)
            try:
                attributions, _ = self.ig.attribute(
                    input_tensors, baselines, target=0, return_convergence_delta=True, n_steps=25
                )
            except Exception:
                attributions, _ = self.ig.attribute(input_tensors, baselines, return_convergence_delta=True, n_steps=25)

            # Aggregation for TCN
            attributions = attributions.abs().sum(dim=0).sum(dim=0)

            # Normalization
            if torch.norm(attributions) > 0:
                attributions = attributions / torch.norm(attributions)

            return attributions.cpu().detach().numpy()
        except Exception as e:
            import logging

            logging.error(f"[CaptumAttributionEngine] Failed to compute importances: {e}", exc_info=True)
            return None
