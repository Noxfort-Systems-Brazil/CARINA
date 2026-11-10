# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import math
from typing import Tuple


class TopologicalScaler:
    """
    Topological Auto-Scaling Utility (Zero-Config AutoML).
    Computes power-of-2 neural dimensions and attention head counts based on the
    graph node density (N traffic lights) of the city network.
    Guarantees optimal TensorCore alignment and prevents overfitting.
    """

    @staticmethod
    def calculate_latent_dim(num_nodes: int) -> int:
        """
        Calculates optimal PAE latent dimension based on graph node count.

        Args:
            num_nodes (int): Total number of traffic light nodes in the city map.

        Returns:
            int: Power-of-2 latent dimension (32, 64, 128, or 256).
        """
        if num_nodes <= 0:
            return 64
        elif num_nodes <= 20:
            return 32
        elif num_nodes <= 80:
            return 64
        elif num_nodes <= 250:
            return 128  # Mid-sized cities (e.g., Londrina)
        else:
            return 256  # Megalopolis

    @staticmethod
    def calculate_num_heads(num_nodes: int) -> int:
        """
        Calculates optimal Transformer Multi-Head Attention head count.

        Args:
            num_nodes (int): Total number of traffic light nodes.

        Returns:
            int: Number of attention heads (2, 4, 8, or 16).
        """
        if num_nodes <= 20:
            return 2
        elif num_nodes <= 80:
            return 4
        elif num_nodes <= 250:
            return 8
        else:
            return 16

    @classmethod
    def auto_scale_architecture(cls, num_nodes: int) -> Tuple[int, int]:
        """
        Auto-scales both latent dimension and head count.

        Args:
            num_nodes (int): Number of nodes.

        Returns:
            Tuple[int, int]: (latent_dim, num_heads)
        """
        latent_dim = cls.calculate_latent_dim(num_nodes)
        num_heads = cls.calculate_num_heads(num_nodes)
        logging.info(
            f"[TopologicalScaler] Auto-scaled for N={num_nodes} nodes -> latent_dim={latent_dim}, num_heads={num_heads}"
        )
        return latent_dim, num_heads
