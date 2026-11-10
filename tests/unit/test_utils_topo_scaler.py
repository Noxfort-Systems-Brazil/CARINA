# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Unit tests for src/utils/topo_scaler.py
"""

import pytest

from src.utils.topo_scaler import TopologicalScaler


class TestTopologicalScaler:
    def test_calculate_latent_dim_all_ranges(self):
        assert TopologicalScaler.calculate_latent_dim(-5) == 64
        assert TopologicalScaler.calculate_latent_dim(0) == 64
        assert TopologicalScaler.calculate_latent_dim(10) == 32
        assert TopologicalScaler.calculate_latent_dim(20) == 32
        assert TopologicalScaler.calculate_latent_dim(50) == 64
        assert TopologicalScaler.calculate_latent_dim(80) == 64
        assert TopologicalScaler.calculate_latent_dim(150) == 128
        assert TopologicalScaler.calculate_latent_dim(250) == 128
        assert TopologicalScaler.calculate_latent_dim(500) == 256

    def test_calculate_num_heads_all_ranges(self):
        assert TopologicalScaler.calculate_num_heads(10) == 2
        assert TopologicalScaler.calculate_num_heads(20) == 2
        assert TopologicalScaler.calculate_num_heads(50) == 4
        assert TopologicalScaler.calculate_num_heads(80) == 4
        assert TopologicalScaler.calculate_num_heads(150) == 8
        assert TopologicalScaler.calculate_num_heads(250) == 8
        assert TopologicalScaler.calculate_num_heads(400) == 16

    def test_auto_scale_architecture(self):
        latent_dim, num_heads = TopologicalScaler.auto_scale_architecture(100)
        assert latent_dim == 128
        assert num_heads == 8

        latent_dim, num_heads = TopologicalScaler.auto_scale_architecture(15)
        assert latent_dim == 32
        assert num_heads == 2
