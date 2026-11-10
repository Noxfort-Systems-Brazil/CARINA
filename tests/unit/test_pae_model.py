# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import subprocess
import sys
import tempfile
import pytest
import torch
from unittest.mock import MagicMock

from src.models.pae import PredictiveAutoencoder
from src.optimizer.pae_optimizer import PAEOptimizer
from src.core.strategic_coordinator import StrategicCoordinator
from src.utils.locale_manager_backend import LocaleManagerBackend


class TestPredictiveAutoencoder:
    """Unit tests for the Universal Predictive Autoencoder (PAE), PAEOptimizer and its coordination layer."""

    def test_pae_instantiation_and_eval_mode(self):
        """Verifies that PAE instantiates correctly as a pure nn.Module in evaluation mode."""
        pae = PredictiveAutoencoder(input_dim=40, latent_dim=16, history_len=8)
        assert pae.input_dim == 40
        assert pae.latent_dim == 16
        assert pae.history_len == 8
        assert not pae.training, "PAE should default to evaluation mode upon instantiation"
        assert pae.device is not None
        assert not hasattr(pae, "optimizer"), "Pure nn.Module PAE should not hold an internal optimizer"

    def test_pae_optimizer_instantiation(self):
        """Verifies that PAEOptimizer instantiates properly."""
        optimizer = PAEOptimizer(learning_rate=1e-3)
        assert optimizer.learning_rate == 1e-3
        assert optimizer.device is not None
        assert optimizer.scaler is not None

    def test_strategic_coordinator_pae_injection(self):
        """Verifies StrategicCoordinator properly stores shared_pae."""
        mock_settings = {
            "GAT_STRATEGIST": {
                "update_frequency_seconds": "5",
                "output_dim": "8",
                "temporal_window": "12",
            }
        }
        mock_locale = LocaleManagerBackend()
        pae = PredictiveAutoencoder(input_dim=20, latent_dim=16, history_len=8)

        coord = StrategicCoordinator(
            settings=mock_settings, device="cpu", locale_manager=mock_locale, shared_pae=pae
        )
        assert coord.shared_pae is pae

    def test_pae_real_torch_math_end_to_end(self):
        """
        Executes end-to-end real PyTorch mathematical verification in an isolated process
        to validate real forward, backward, padding, PAEOptimizer and checkpointing without mock overrides.
        """
        verify_script = """
import os
import tempfile
import torch
from src.models.pae import PredictiveAutoencoder
from src.optimizer.pae_optimizer import PAEOptimizer

# 1. Instantiation and Eval mode (Pure nn.Module)
pae = PredictiveAutoencoder(input_dim=30, latent_dim=16, history_len=8)
assert not pae.training, 'PAE should be in eval mode'
assert not hasattr(pae, 'optimizer'), 'PAE should not have optimizer attribute'

# 2. 3D Sequence Encoding & Decoding
x_3d = torch.randn(2, 6, 30)
z_3d = pae.encode(x_3d)
assert z_3d.shape == (2, 16), f'Unexpected latent shape: {z_3d.shape}'
pred_3d = pae.decode(z_3d)
assert pred_3d.shape == (2, 30), f'Unexpected reconstructed shape: {pred_3d.shape}'

# 3. Heterogeneous Dimension Padding
x_small = torch.randn(2, 4, 10)
z_small = pae.encode(x_small)
assert z_small.shape == (2, 16), f'Padding failed for small tensor: {z_small.shape}'

# 4. Decoupled PAEOptimizer: Batched Self-Supervised Training Step
pae_opt = PAEOptimizer(learning_rate=1e-3, device=torch.device('cpu'))
batch_curr = torch.randn(4, 8, 30)
batch_next = torch.randn(4, 30)
loss_batch = pae_opt.step(pae, batch_curr, batch_next)
assert isinstance(loss_batch, float) and loss_batch >= 0.0, f'Invalid loss: {loss_batch}'
assert not pae.training, 'PAE should restore eval mode after optimization step'

# 5. Decoupled PAEOptimizer: Unbatched 2D/1D Training Step
curr_2d = torch.randn(8, 30)
next_1d = torch.randn(30)
loss_2d = pae_opt.step(pae, curr_2d, next_1d)
assert isinstance(loss_2d, float) and loss_2d >= 0.0

# 6. Checkpoint Serialization (.pth)
with tempfile.TemporaryDirectory() as tmpdir:
    ckpt_path = os.path.join(tmpdir, 'pae_universal.pth')
    torch.save(pae.state_dict(), ckpt_path)
    assert os.path.exists(ckpt_path), 'Checkpoint file was not created'

    pae_restored = PredictiveAutoencoder(input_dim=30, latent_dim=16, history_len=8)
    pae_restored.load_state_dict(torch.load(ckpt_path, weights_only=True))
    assert torch.allclose(pae.encode(x_3d).cpu(), pae_restored.encode(x_3d).cpu(), atol=1e-5)

print('PAE_REAL_TORCH_VERIFIED')
"""
        cmd = [sys.executable, "-c", verify_script]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 0, f"Subprocess failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
        assert "PAE_REAL_TORCH_VERIFIED" in res.stdout
