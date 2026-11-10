# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import configparser
import logging
import os
import sys
from collections import defaultdict
from typing import Any, Dict

import numpy as np

try:
    from torch.utils.tensorboard import SummaryWriter

    TENSORBOARD_AVAILABLE = True
except ImportError:
    TENSORBOARD_AVAILABLE = False

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


class MetricsTracker:
    """
    Tracks and aggregates PPO metrics (Rewards and Entropies) during an Episode.
    """

    def __init__(self):
        self.episode_metrics = defaultdict(lambda: {"reward": 0.0, "entropies": []})

        self.config = configparser.ConfigParser()
        settings_path = os.path.join(project_root, "config", "settings.ini")
        if os.path.exists(settings_path):
            self.config.read(settings_path)

        self.tb_enabled = self.config.getboolean("TENSORBOARD", "tensorboard_enabled", fallback=False)
        self.tb_log_dir = self.config.get("TENSORBOARD", "tensorboard_log_dir", fallback="results/tensorboard")

        self.writer = None
        if self.tb_enabled and TENSORBOARD_AVAILABLE:
            from utils.paths import get_base_output_dir

            full_log_dir = os.path.join(get_base_output_dir(), self.tb_log_dir)
            os.makedirs(full_log_dir, exist_ok=True)
            self.writer = SummaryWriter(log_dir=full_log_dir)
            logging.info(f"[MetricsTracker] TensorBoard habilitado em: {full_log_dir}")
        elif self.tb_enabled and not TENSORBOARD_AVAILABLE:
            logging.warning(
                "[MetricsTracker] TensorBoard ativado via config, mas biblioteca não instalada (pip install tensorboard)."
            )

    def record_step(self, rewards: Dict[str, float], entropies: Dict[str, float]):
        if rewards:
            for tl_id, reward in rewards.items():
                self.episode_metrics[tl_id]["reward"] += reward

        if entropies:
            for tl_id, entropy in entropies.items():
                self.episode_metrics[tl_id]["entropies"].append(entropy)

    def finalize_episode(self, episode_number: int = None) -> Dict[str, Dict[str, float]]:
        final_metrics: Dict[str, Dict[str, float]] = {}

        for tl_id, data in self.episode_metrics.items():
            mean_entropy = np.mean(data["entropies"]) if data["entropies"] else 0.0
            final_metrics[tl_id] = {"reward": data["reward"], "entropy": mean_entropy}

            if self.writer and episode_number is not None:
                self.writer.add_scalar(f"Reward/{tl_id}", data["reward"], episode_number)
                self.writer.add_scalar(f"Entropy/{tl_id}", mean_entropy, episode_number)

        return final_metrics

    def close(self):
        if self.writer:
            self.writer.close()
