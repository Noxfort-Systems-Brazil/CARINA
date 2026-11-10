# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from collections import deque
from typing import Any, Dict, Tuple

import numpy as np
import torch


class InputPreprocessor:
    """
    Handles the temporal stacking and tensor conversion of state vectors.

    This component manages the short-term history (deque) required for
    sequence-based models (LSTM/TCN) and prepares the raw data for
    PyTorch inference, keeping the main Trainer loop clean.
    """

    def __init__(self, sequence_length: int, device: torch.device):
        """
        Args:
            sequence_length: Number of past frames to stack (e.g., 4).
            device: Torch device (CPU/CUDA) where tensors should be sent.
        """
        self.sequence_length = sequence_length
        self.device = device

        # Stores the history for each traffic light: {tl_id: deque([state_t-3, ..., state_t])}
        self.state_history: Dict[str, deque] = {}

    def reset(self):
        """Clears all stored history. Call this when loading a new map."""
        self.state_history.clear()

    def prepare_tensor(self, tl_id: str, state_vector: np.ndarray) -> Tuple[torch.Tensor, np.ndarray]:
        """
        Processes a single state vector into a model-ready tensor.

        1. Initializes history with zeros if this is the first time seeing tl_id.
        2. Appends the new state to the history deque (auto-removing oldest).
        3. Stacks the sequence into a numpy array.
        4. Converts to a PyTorch FloatTensor and moves to device.

        Args:
            tl_id: The ID of the intersection.
            state_vector: 1D numpy array representing current state.

        Returns:
            Tuple containing:
            - state_tensor: [1, seq_len, input_dim] tensor on device.
            - state_seq: The numpy sequence used (useful for memory storage).
        """
        # Initialize history if new agent/intersection
        if tl_id not in self.state_history:
            self.state_history[tl_id] = deque(maxlen=self.sequence_length)
            # Pad with zeros so the model has a full sequence immediately
            for _ in range(self.sequence_length):
                self.state_history[tl_id].append(np.zeros_like(state_vector))

        # Update history
        self.state_history[tl_id].append(state_vector)

        # Create Sequence
        # shape: [sequence_length, input_dim]
        state_seq = np.array(self.state_history[tl_id], dtype=np.float32)

        # Convert to Tensor
        # Unsqueeze(0) creates the batch dimension -> [1, sequence_length, input_dim]
        state_tensor = torch.FloatTensor(state_seq).unsqueeze(0).to(self.device)

        return state_tensor, state_seq
