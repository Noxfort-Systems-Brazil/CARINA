# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import TYPE_CHECKING, Any, Tuple

import numpy as np
import torch

if TYPE_CHECKING:
    from agents.local_agent import LocalAgent


class InferenceEngine:
    """
    Handles the tensor translation and Neural Network interface for LocalAgents.
    """

    def predict(self, agent: "LocalAgent", state_sequence: list) -> Tuple[int, Any, Any, Any, Any]:
        """
        Converts sequence to tensor, infers action, and returns components for PPO training.
        Returns: (suggested_action_int, action_tensor, log_prob, state_value, entropy)
        """
        seq_np = np.array(state_sequence, dtype=np.float32)
        state_sequence_tensor = torch.from_numpy(seq_np).unsqueeze(0).to(agent.device)

        # Enable AMP (Automatic Mixed Precision) and TensorCores for forward inference
        device_type = agent.device.type
        with torch.amp.autocast(device_type=device_type, enabled=(device_type == "cuda")):
            action_tensor, log_prob, state_val, dist_entropy = agent.choose_action(state_sequence_tensor)
            suggested_action = action_tensor.item()

        return suggested_action, action_tensor, log_prob, state_val, dist_entropy
