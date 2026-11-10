# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from collections import deque
from typing import Any, Deque, Optional

import torch
import torch.nn.functional as F


class TemporalSequenceManager:
    """
    Manages sliding-window temporal node features and self-supervised prediction horizons.
    Provides 3D spatiotemporal tensor aggregation with padding for graph attention networks.
    """

    def __init__(self, temporal_window: int = 12):
        self.temporal_window = temporal_window
        self.temporal_buffer: Deque[torch.Tensor] = deque(maxlen=self.temporal_window)
        self.prediction_target_time: Optional[float] = None
        self.cached_future_pred: Optional[torch.Tensor] = None

    def evaluate_and_train_prediction(
        self,
        sim_time: float,
        current_features: torch.Tensor,
        gat_model: Any,
    ) -> None:
        """Executes online self-supervised training step if the prediction horizon has elapsed."""
        if self.cached_future_pred is not None and self.prediction_target_time is not None:
            if sim_time >= self.prediction_target_time:
                try:
                    pred_loss = F.mse_loss(self.cached_future_pred, current_features)
                    if hasattr(gat_model, "update"):
                        gat_model.update(pred_loss)
                except Exception as train_err:
                    logging.debug(f"[TemporalSequenceManager] Self-supervised training error: {train_err}")
                self.cached_future_pred = None
                self.prediction_target_time = None

    def append_features(self, features_tensor: torch.Tensor) -> None:
        """Appends snapshot features to the sliding buffer."""
        self.temporal_buffer.append(features_tensor)

    def build_temporal_sequence(self) -> torch.Tensor:
        """
        Constructs 3D spatiotemporal tensor: [num_nodes, temporal_window, max_state_dim].
        Applies edge padding when sliding window buffer is not yet full.
        """
        if len(self.temporal_buffer) < self.temporal_window:
            pad_count = self.temporal_window - len(self.temporal_buffer)
            pads = [self.temporal_buffer[0]] * pad_count
            return torch.stack(pads + list(self.temporal_buffer), dim=1)
        return torch.stack(list(self.temporal_buffer), dim=1)

    def cache_prediction(self, future_pred: torch.Tensor, target_time: float) -> None:
        """Stores predicted future representation and scheduled target simulation time."""
        self.cached_future_pred = future_pred
        self.prediction_target_time = target_time
