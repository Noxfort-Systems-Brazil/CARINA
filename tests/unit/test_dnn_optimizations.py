# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from unittest.mock import MagicMock, patch
import numpy as np
import pytest
import torch

from src.models.pae import PredictiveAutoencoder
from src.utils.local_agent_helpers import PAEStateAugmentor
from src.agents.local_agent import LocalAgent
from src.agents.guardian_agent import GuardianAgent
from src.engine.agent_evaluator import AgentEvaluator
from src.core.enums import Maturity


def test_pae_state_augmentor_with_precomputed_latent():
    """Verify that PAEStateAugmentor skips encode when precomputed_latent is provided."""
    mock_pae = MagicMock()
    mock_pae.latent_dim = 4
    augmentor = PAEStateAugmentor(mock_pae)

    # Fake input state: [batch=1, seq_len=4, obs_dim=6]
    state_tensor = torch.zeros(1, 4, 6)
    precomputed = torch.tensor([[1.0, 2.0, 3.0, 4.0]])

    augmented = augmentor.augment(state_tensor, precomputed_latent=precomputed)

    # Check shape: [1, 4, 6 + 4] = [1, 4, 10]
    assert augmented.shape == (1, 4, 10)
    # Ensure encode was NOT called on the mock PAE
    mock_pae.encode.assert_not_called()
    # Check that latent was concatenated properly across the sequence
    assert torch.allclose(augmented[0, 0, 6:], precomputed[0])
    assert torch.allclose(augmented[0, 3, 6:], precomputed[0])


def test_pae_batched_forward_consistency():
    """Verify that batched encoding matches individual encoding slice-by-slice."""
    if type(torch).__name__ == "DummyTorch":
        # In DummyTorch mode, test that encode accepts 3D stacked batches without error
        from tests.mocks.dummy_tensor import DummyTensor

        pae = PredictiveAutoencoder(input_dim=10, latent_dim=4, history_len=8, d_model=16, nhead=2, num_layers=1)
        stacked_batch = DummyTensor(None, shape=(3, 8, 10))
        out = pae.encode(stacked_batch)
        assert out is not None
        return

    input_dim = 10
    latent_dim = 4
    history_len = 8

    pae = PredictiveAutoencoder(
        input_dim=input_dim,
        latent_dim=latent_dim,
        history_len=history_len,
        d_model=16,
        nhead=2,
        num_layers=1,
    )
    pae.eval()

    torch.manual_seed(42)
    sample_1 = torch.randn(1, history_len, input_dim)
    sample_2 = torch.randn(1, history_len, input_dim)
    sample_3 = torch.randn(1, history_len, input_dim)

    stacked_batch = torch.cat([sample_1, sample_2, sample_3], dim=0)

    with torch.no_grad():
        batched_latents = pae.encode(stacked_batch)
        latent_1 = pae.encode(sample_1)
        latent_2 = pae.encode(sample_2)
        latent_3 = pae.encode(sample_3)

    assert batched_latents.shape == (3, latent_dim)
    assert torch.allclose(batched_latents[0:1], latent_1, atol=1e-5)
    assert torch.allclose(batched_latents[1:2], latent_2, atol=1e-5)
    assert torch.allclose(batched_latents[2:3], latent_3, atol=1e-5)


def test_local_agent_choose_action_with_precomputed_latent():
    """Verify that LocalAgent.choose_action accepts precomputed_pae_latent and uses it."""
    mock_locale = MagicMock()
    mock_locale.get_string.return_value = "Test"

    hyperparams = {
        "gamma": 0.99,
        "gae_lambda": 0.95,
        "learning_rate": 0.001,
        "eps_clip": 0.2,
        "k_epochs": 1,
        "target_kl": 0.02,
        "grad_clip_norm": 0.5,
        "dropout_p": 0.0,
        "sequence_length": 4,
    }

    mock_pae = MagicMock()
    mock_pae.latent_dim = 4

    agent = LocalAgent(
        tlight_id="TL_TEST",
        n_observations=8,
        n_actions=2,
        initial_hyperparams=hyperparams,
        log_dir="/tmp",
        locale_manager=mock_locale,
        shared_pae=mock_pae,
    )

    state_tensor = torch.randn(1, 4, 8)
    precomputed = torch.randn(1, 4)

    # Inference with precomputed latent
    action_idx, log_prob, val, entropy = agent.choose_action(
        state_tensor, precomputed_pae_latent=precomputed
    )

    assert action_idx is not None
    # Verify mock_pae.encode was never called
    mock_pae.encode.assert_not_called()


def test_guardian_agent_select_action_with_precomputed_latent():
    """Verify that GuardianAgent respects precomputed_pae_latent in select_action."""
    mock_locale = MagicMock()
    mock_locale.get_string.return_value = "OK"

    mock_pae = MagicMock()
    mock_pae.latent_dim = 4

    aiconfig = MagicMock()
    aiconfig.getint.side_effect = lambda k, fallback=None: fallback if fallback else 128
    aiconfig.getfloat.side_effect = lambda k, fallback=None: fallback if fallback else 0.5

    guardian = GuardianAgent(
        aiconfig=aiconfig,
        traffic_rules_config=aiconfig,
        locale_manager=mock_locale,
        shared_pae=mock_pae,
    )

    state_vec = [0.1] * 8
    context = {
        "tl_id": "TL_GUARD",
        "current_stage_duration": 10.0,
        "current_stage_state": "G",
        "max_green_time": 60.0,
        "spillback_risk_threshold": 0.9,
    }

    precomputed = torch.zeros((1, 4))
    action, reason = guardian.select_action(state_vec, context, precomputed_pae_latent=precomputed)

    assert action in (0, 1)
    # mock_pae.encode should NOT have been called because precomputed was passed
    mock_pae.encode.assert_not_called()


def test_pae_optimize_engine_fallback():
    """Verify optimize_engine runs safely even when torch.compile is disabled or simulated."""
    pae = PredictiveAutoencoder(input_dim=8, latent_dim=4, history_len=4, d_model=8, nhead=1, num_layers=1)
    # enable_compile=False should return immediately
    pae.optimize_engine(enable_compile=False)

    # Calling with eager fallback simulation
    with patch.object(torch, "compile", side_effect=RuntimeError("Test fallback")):
        pae.optimize_engine(enable_compile=True)
        # Should not raise exception
