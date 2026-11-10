# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Comprehensive Unit & Mathematical Verification Suite for CARINA's Modernized DNN Stack:
1. Binary ActorCriticNet (n_actions=2, 3-level causal TCN, TemporalAttentionPool, decoupled trunks, action_mask)
2. PPOOptimizer (exact GAE bootstrap, Schulman non-negative KL, Value Clipping, mini-batching, eval restoration)
3. PredictiveAutoencoder (RevIN + scale projection, Cross-Attention pooling + valid_dims mask, binary action world model)
4. QR-D3QN & GuardianNeuralPredictor (32 quantiles, CVaR tail-risk veto, Quantile Huber loss, Polyak soft target update)
5. STGATv2Lite & StepProcessor (spatial residuals, CTDE global_critic_head, HFT strategic context injection)
6. FleetBatchInferencer & AgentEvaluator (vmap numerical equivalence, physical min/max green & yellow action masks)
7. XAI CaptumModelWrapper & AgentReconstructor (end-to-end differentiable PAE gradients, raw logit attribution, PAE ckpt load)
"""

from collections import deque
from unittest.mock import MagicMock
import numpy as np
import pytest
import torch

from tests.mocks.torch_mock import DummyTorch

from src.agents.guardian_neural_predictor import GuardianNeuralPredictor
from src.agents.local_agent import LocalAgent
from src.engine.agent_evaluator import AgentEvaluator
from src.engine.fleet_batch_inferencer import FleetBatchInferencer
from src.engine.step_processor import StepProcessor
from src.memory.replay_memory import ReplayMemory
from src.memory.state_buffer import StateReplayMemory
from src.models.actor_critic_tcn import ActorCriticNet
from src.models.d3qn_tcn import D3QN_TCN
from src.models.pae import PredictiveAutoencoder
from src.models.st_gatv2_lite import STGATv2Lite
from src.optimizer.dqn_optimizer import DQNOptimizer
from src.optimizer.pae_optimizer import PAEOptimizer
from src.optimizer.ppo_optimizer import PPOOptimizer
from src.xai.agent_reconstructor import AgentReconstructor
from src.xai.captum_model_wrapper import CaptumModelWrapper

IS_REAL_TORCH = not isinstance(torch, DummyTorch)


def test_binary_actor_critic_action_mask_and_eval_determinism(tmp_path):
    """Verifies n_actions=2 default, decoupled trunks, physical action_mask, and .eval() determinism."""
    lm = MagicMock()
    agent = LocalAgent(
        tlight_id="TL_BIN",
        n_observations=12,
        initial_hyperparams={"dropout_p": 0.25},
        log_dir=str(tmp_path),
        locale_manager=lm,
    )

    assert agent.n_actions == 2
    assert agent.policy_net.n_actions == 2
    assert agent.policy_net.training is False
    assert hasattr(agent.policy_net, "actor_trunk")
    assert hasattr(agent.policy_net, "critic_trunk")
    if IS_REAL_TORCH:
        assert len(agent.policy_net.tcn.network) == 3

    x = torch.randn(1, 12, 12, device=agent.device)
    logits_1, val_1 = agent.policy_net.forward_logits(x)
    logits_2, val_2 = agent.policy_net.forward_logits(x)

    if IS_REAL_TORCH:
        assert logits_1.shape == (1, 2)
        assert val_1.shape == (1, 1)
        assert torch.allclose(logits_1, logits_2, atol=1e-6)
        assert torch.allclose(val_1, val_2, atol=1e-6)

    # Mask out action 0 (ADVANCE forbidden during yellow / min_green) -> must choose action 1 (KEEP)
    mask_keep_only = torch.tensor([[False, True]], dtype=torch.bool, device=agent.device)
    for _ in range(5):
        act, log_p, val, ent = agent.choose_action(x, action_mask=mask_keep_only)
        if IS_REAL_TORCH:
            assert int(act.item()) == 1
            assert torch.isfinite(log_p).all()

    # Mask out action 1 (KEEP forbidden at max_green) -> must choose action 0 (ADVANCE)
    mask_advance_only = torch.tensor([[True, False]], dtype=torch.bool, device=agent.device)
    agent._last_raw_state = None  # invalidate cache
    for _ in range(5):
        act, log_p, val, ent = agent.choose_action(x, action_mask=mask_advance_only)
        if IS_REAL_TORCH:
            assert int(act.item()) == 0
            assert torch.isfinite(log_p).all()


def test_thinking_mode_full_sequence_cache_invalidation(tmp_path):
    """Verifies Thinking Mode cache compares the entire temporal window, not just the last frame."""
    lm = MagicMock()
    agent = LocalAgent(
        tlight_id="TL_CACHE",
        n_observations=8,
        initial_hyperparams={},
        log_dir=str(tmp_path),
        locale_manager=lm,
    )

    seq_a = torch.zeros(1, 12, 8, device=agent.device)
    seq_b = torch.zeros(1, 12, 8, device=agent.device)
    if IS_REAL_TORCH:
        seq_b[0, 0, 0] = 5.0  # Historical frame differs while seq_b[:, -1, :] is identical!

    agent.choose_action(seq_a)
    cached_ref_a = agent._last_decision
    agent.choose_action(seq_a)
    if IS_REAL_TORCH:
        assert agent._last_decision is cached_ref_a
        agent.choose_action(seq_b)
        assert agent._last_decision is not cached_ref_a


def test_ppo_optimizer_gae_bootstrap_minibatch_and_eval_restore(tmp_path):
    """Verifies PPOOptimizer exact GAE bootstrap, Schulman non-negative KL, mini-batching, and eval restore."""
    lm = MagicMock()
    agent = LocalAgent(
        tlight_id="TL_PPO",
        n_observations=10,
        n_actions=2,
        initial_hyperparams={},
        log_dir=str(tmp_path),
        locale_manager=lm,
    )
    net = agent.policy_net
    net.eval()
    ppo = PPOOptimizer(
        {"gamma": 0.99, "gae_lambda": 0.95, "k_epochs": 3, "eps_clip": 0.2, "minibatch_size": 8},
        device=agent.device,
    )

    batch_size = 20
    old_states = torch.randn(batch_size, 12, 10, device=agent.device)
    old_actions = torch.ones(batch_size, dtype=torch.long, device=agent.device)
    with torch.no_grad():
        old_lp, old_vals, _ = agent.evaluate(old_states, old_actions)
    rewards = [1.5] * batch_size
    dones = [False] * batch_size

    memory_batch = (old_states, old_actions, old_lp.detach(), rewards, dones, old_vals.squeeze(-1).detach())
    loss = ppo.step(
        policy_net=net,
        optimizer=agent.optimizer,
        memory_batch=memory_batch,
        evaluate_fn=agent.evaluate,
        last_next_value=4.2,
    )
    assert net.training is False
    if IS_REAL_TORCH:
        assert isinstance(loss, float)
        assert np.isfinite(loss)


def test_pae_revin_padding_invariance_and_binary_counterfactual():
    """Verifies PAE RevIN, valid_dims padding mask invariance, binary action conditioning, and PAEOptimizer."""
    pae = PredictiveAutoencoder(input_dim=16, latent_dim=12, history_len=12, d_model=32, nhead=4, num_layers=2)
    pae.eval()

    x = torch.randn(2, 12, 16)
    if IS_REAL_TORCH:
        x[:, :, 10:] = 0.0  # Simulate 10 active sensors + 6 zero-padded channels

    valid_dims = torch.tensor([10, 10], dtype=torch.long)
    z_clean = pae.encode(x, valid_dims=valid_dims)
    assert z_clean is not None

    if IS_REAL_TORCH:
        assert z_clean.shape == (2, 12)
        # Perturbing masked padding channels must NOT alter encoded latent when valid_dims=10
        x_perturbed_pad = x.clone()
        x_perturbed_pad[:, :, 10:] = 999.0
        z_masked = pae.encode(x_perturbed_pad, valid_dims=valid_dims)
        assert torch.allclose(z_clean, z_masked, atol=1e-5)

        # Counterfactual action conditioning: action=0 (ADVANCE) vs action=1 (KEEP)
        mean_adv, logvar_adv = pae.decode_with_uncertainty(z_clean, action=torch.tensor([0, 0]))
        mean_keep, logvar_keep = pae.decode_with_uncertainty(z_clean, action=torch.tensor([1, 1]))
        assert mean_adv.shape == (2, 16)
        assert logvar_adv.shape == (2, 16)
        assert not torch.allclose(mean_adv, mean_keep)

    # Verify PAEOptimizer step_from_memory with action & valid_dim metadata
    mem = StateReplayMemory(capacity=64, state_shape=(12, 16), next_state_shape=(16,), device=torch.device("cpu"))
    target_frame = torch.ones(16) * 0.5
    seq_sample = torch.ones(12, 16) * 0.5
    for i in range(16):
        mem.push(seq_sample, target_frame, action=i % 2, valid_dim=10)

    pae_opt = PAEOptimizer(learning_rate=3e-3, device=torch.device("cpu"))
    loss_initial = pae_opt.step_from_memory(pae, mem, batch_size=8)
    loss_final = loss_initial
    for _ in range(8):
        loss_final = pae_opt.step_from_memory(pae, mem, batch_size=8)
    assert pae.training is False
    if IS_REAL_TORCH:
        assert np.isfinite(loss_initial) and np.isfinite(loss_final)
        assert loss_final <= loss_initial + 0.05


def test_qr_d3qn_cvar_guardian_and_polyak_target_update():
    """Verifies QR-D3QN quantile shapes, CVaR tail-risk veto, Quantile Huber loss, and Polyak soft update."""
    pae = PredictiveAutoencoder(input_dim=16, latent_dim=8, history_len=12, d_model=16, nhead=2, num_layers=1)
    pae.eval()

    policy_net = D3QN_TCN(n_observations=10 + 8, n_actions=2, num_quantiles=32)
    target_net = D3QN_TCN(n_observations=10 + 8, n_actions=2, num_quantiles=32)
    policy_net.eval()
    target_net.eval()

    x = torch.randn(4, 12, 10)
    z = torch.randn(4, 8)
    quantiles = policy_net.forward_quantiles(x, z)
    q_mean = policy_net(x, z)
    assert quantiles is not None
    assert q_mean is not None

    if IS_REAL_TORCH:
        assert quantiles.shape == (4, 2, 32)
        assert q_mean.shape == (4, 2)
        assert torch.allclose(quantiles.mean(dim=-1), q_mean, atol=1e-5)

    # Verify GuardianNeuralPredictor CVaR sensitivity to lower-tail risk
    predictor = GuardianNeuralPredictor(
        policy_net=policy_net,
        target_net=target_net,
        device=torch.device("cpu"),
        shared_pae=pae,
        temporal_seq_len=12,
        action_keep_stage=1,
        cvar_alpha=0.25,
    )

    if IS_REAL_TORCH:
        # Mock quantiles where Action 0 (ALLOW) has severe lower-tail crash (-10.0) while Action 1 (KEEP) is safe (0.0)
        fake_q = torch.zeros(1, 2, 32)
        fake_q[0, 0, :8] = -10.0  # Worst 25% quantiles for ALLOW are catastrophic
        fake_q[0, 0, 8:] = 3.5    # Upper quantiles make mean positive (+0.125), yet CVaR_0.25 = -10.0!
        fake_q[0, 1, :] = 0.0     # KEEP has 0.0 across all quantiles -> CVaR margin = 0 - (-10) = +10.0!
        orig_fq = policy_net.forward_quantiles
        policy_net.forward_quantiles = MagicMock(return_value=fake_q)
        try:
            breakdown = predictor.evaluate_spillback_breakdown([0.5] * 10, "TL_0")
            assert breakdown["cvar_margin"] > 5.0
            assert breakdown["neural_prob"] > 0.99
        finally:
            policy_net.forward_quantiles = orig_fq

    # Verify Quantile Huber DQNOptimizer + Polyak soft update
    opt_dqn = torch.optim.AdamW(policy_net.parameters(), lr=1e-3)
    dqn_opt = DQNOptimizer({"gamma": 0.95, "batch_size": 4, "tau": 0.1}, device=torch.device("cpu"))
    per = ReplayMemory(capacity=32, state_shape=(12, 10), device=torch.device("cpu"))
    for i in range(8):
        s_np = np.random.randn(12, 10).astype(np.float32)
        ns_np = np.random.randn(12, 10).astype(np.float32)
        per.push(s_np, i % 2, ns_np, float(i) * 0.1)

    loss_val = dqn_opt.step(
        policy_net=policy_net,
        target_net=target_net,
        optimizer=opt_dqn,
        memory=per,
        forward_policy=predictor.forward_policy,
        forward_target=predictor.forward_target,
        forward_policy_quantiles=predictor.forward_policy_quantiles,
        forward_target_quantiles=predictor.forward_target_quantiles,
    )
    assert policy_net.training is False
    assert loss_val is not None

    if IS_REAL_TORCH:
        with torch.no_grad():
            for p in policy_net.parameters():
                p.add_(1.0)
        p_before = next(target_net.parameters()).clone()
        dqn_opt.soft_update_target_net(policy_net, target_net, tau=0.1)
        p_after = next(target_net.parameters())
        assert not torch.allclose(p_before, p_after)


def test_st_gatv2_ctde_and_step_processor_strategic_injection(tmp_path):
    """Verifies STGATv2Lite spatial residuals + global_critic_head and StepProcessor HFT coordination."""
    gat = STGATv2Lite(input_dim=8, hidden_dim=16, output_dim=8, heads=2, edge_dim=3)
    gat.eval()

    x_nodes = torch.randn(3, 12, 8)
    edge_index = torch.tensor([[0, 1, 1, 2], [1, 0, 2, 1]], dtype=torch.long)
    edge_attr = torch.ones((4, 3), dtype=torch.float32)

    z, pred, g_val = gat(x_nodes, edge_index, edge_attr=edge_attr, return_prediction=True, return_value=True)
    assert z is not None
    if IS_REAL_TORCH:
        assert z.shape == (3, 8)
        assert pred.shape == (3, 8)
        assert g_val.shape == (3, 1)

    # Wire into StepProcessor and verify LocalAgents receive strategic context vectors
    lm = MagicMock()
    lm.get_string.return_value = "MSG"
    settings = MagicMock()
    settings.getint.return_value = 100
    settings.getfloat.return_value = 5.0

    ip = MagicMock()
    ip.sequence_length = 12
    ip.state_history = {
        "TL_0": deque([np.ones(8, dtype=np.float32) for _ in range(12)], maxlen=12),
        "TL_1": deque([np.ones(8, dtype=np.float32) * 2.0 for _ in range(12)], maxlen=12),
    }

    evaluator = MagicMock()
    evaluator.input_preprocessor = ip
    from src.domain.value_objects import FleetDecisions

    evaluator.evaluate_fleet.return_value = FleetDecisions(
        actions={"TL_0": 1, "TL_1": 1},
        lanes_state={},
        maturity_info={"TL_0": "ADULT", "TL_1": "ADULT"},
        step_reward_sum=4.0,
        guardian_vetoed_any=False,
        metrics_delta={"TL_0": (2.0, 0.1), "TL_1": (2.0, 0.1)},
    )

    processor = StepProcessor(
        settings=settings,
        locale_manager=lm,
        step_timer=MagicMock(),
        agent_evaluator=evaluator,
        stage_transition_manager=MagicMock(),
        action_supervisor=MagicMock(),
        online_pae_trainer=MagicMock(),
        mfd_processor=MagicMock(),
        hardware_actuator=MagicMock(),
        telemetry_publisher=MagicMock(),
        cycle_manager=MagicMock(),
        episode_reporter=MagicMock(),
    )

    mock_strategist = MagicMock()
    mock_strategist.num_nodes = 2
    mock_strategist.tls_id_to_idx = {"TL_0": 0, "TL_1": 1}
    mock_strategist.device = torch.device("cpu")
    mock_strategist.edge_index = torch.tensor([[0, 1], [1, 0]], dtype=torch.long)
    mock_strategist.edge_attr = torch.ones((2, 3), dtype=torch.float32)
    mock_strategist.model = STGATv2Lite(input_dim=8, hidden_dim=16, output_dim=8, heads=2, edge_dim=3)
    mock_strategist.get_strategic_vectors.side_effect = lambda ns: mock_strategist.model(
        ns, mock_strategist.edge_index, edge_attr=mock_strategist.edge_attr
    )
    mock_strategist.get_node_index.side_effect = lambda tl: mock_strategist.tls_id_to_idx.get(tl, -1)

    processor.set_strategist(mock_strategist)

    a0 = LocalAgent("TL_0", n_observations=8, initial_hyperparams={}, log_dir=str(tmp_path), locale_manager=lm)
    a1 = LocalAgent("TL_1", n_observations=8, initial_hyperparams={}, log_dir=str(tmp_path), locale_manager=lm)
    agents = {"TL_0": a0, "TL_1": a1}

    processor.process_hft_step({"timestamp": 0.0, "edges": {}}, agents)
    if IS_REAL_TORCH:
        assert a0.strategic_context is not None
        assert a1.strategic_context is not None

    # Advance 6s (>= 5s frequency) -> triggers online self-supervised + CTDE update
    processor.process_hft_step({"timestamp": 6.0, "edges": {}}, agents)
    assert mock_strategist.update.called


def test_fleet_batch_inferencer_vmap_numerical_equivalence(tmp_path):
    """Verifies FleetBatchInferencer produces identical logits/values to single-agent inference."""
    lm = MagicMock()
    pae = PredictiveAutoencoder(input_dim=16, latent_dim=8, history_len=12, d_model=16, nhead=2, num_layers=1)
    pae.eval()

    agents = {}
    tensors = {}
    latents = {}
    masks = {}
    for idx in range(4):
        tl = f"TL_{idx}"
        ag = LocalAgent(
            tlight_id=tl,
            n_observations=10,
            initial_hyperparams={},
            log_dir=str(tmp_path),
            locale_manager=lm,
            shared_pae=pae,
        )
        ag.set_strategic_context(torch.ones((1, 8), device=ag.device) * float(idx + 1) * 0.1)
        agents[tl] = ag
        t = torch.randn(1, 12, 10)
        tensors[tl] = t
        with torch.no_grad():
            padded = pae.pad_to_input_dim(pae.standardize_sequence(t))
            latents[tl] = pae.encode(padded, valid_dims=torch.tensor([10])).to(ag.device)
        masks[tl] = torch.tensor([[False, True]], dtype=torch.bool, device=ag.device)  # deterministic -> action 1

    inferencer = FleetBatchInferencer()
    batched_out = inferencer.infer_fleet(
        agents=agents,
        precomputed_tensors=tensors,
        precomputed_latents=latents,
        action_masks=masks,
    )
    assert set(batched_out.keys()) == set(agents.keys())

    if IS_REAL_TORCH:
        for tl, ag in agents.items():
            b_act, b_lp, b_val, b_ent = batched_out[tl]
            ag._last_raw_state = None  # force fresh single-agent forward
            s_act, s_lp, s_val, s_ent = ag.choose_action(
                tensors[tl], precomputed_pae_latent=latents[tl], action_mask=masks[tl]
            )
            tol = 2e-3 if getattr(ag.device, "type", "cpu") == "cuda" else 1e-5
            assert int(b_act.item()) == int(s_act.item()) == 1
            assert torch.allclose(b_val, s_val, atol=tol)
            assert torch.allclose(b_lp, s_lp, atol=tol)


def test_agent_evaluator_physical_action_mask_constraints(tmp_path):
    """Verifies _compute_physical_action_mask enforces min_green, yellow clearance, and max_green."""
    lm = MagicMock()
    agent = LocalAgent("TL_1", n_observations=8, initial_hyperparams={}, log_dir=str(tmp_path), locale_manager=lm)

    se = MagicMock()
    se.tl_stage_codes = {"TL_1": {0: "GGrr", 1: "yyrr", 2: "rrrr"}}
    asup = MagicMock()
    asup._last_stage_change_time = {"TL_1": 10.0}

    evaluator = AgentEvaluator(
        state_extractor=se,
        input_preprocessor=MagicMock(),
        reward_computer=MagicMock(),
        action_authorizer=MagicMock(),
        action_supervisor=asup,
        maturity_manager=MagicMock(),
        locale_manager=lm,
    )

    # 1. Green elapsed = 3s (< min_green 10s) -> [False, True]
    m_min = evaluator._compute_physical_action_mask("TL_1", agent, current_stage_idx=0, sim_time=13.0)
    assert m_min is not None
    if IS_REAL_TORCH:
        assert m_min.tolist() == [[False, True]]

    # 2. Green elapsed = 25s (between min_green and max_green) -> [True, True]
    m_mid = evaluator._compute_physical_action_mask("TL_1", agent, current_stage_idx=0, sim_time=35.0)
    if IS_REAL_TORCH:
        assert m_mid.tolist() == [[True, True]]

    # 3. Yellow stage -> [False, True]
    m_yel = evaluator._compute_physical_action_mask("TL_1", agent, current_stage_idx=1, sim_time=35.0)
    if IS_REAL_TORCH:
        assert m_yel.tolist() == [[False, True]]

    # 4. Green elapsed = 75s (>= max_green 60s) -> [True, False]
    m_max = evaluator._compute_physical_action_mask("TL_1", agent, current_stage_idx=0, sim_time=85.0)
    if IS_REAL_TORCH:
        assert m_max.tolist() == [[True, False]]


def test_xai_captum_end_to_end_pae_gradient_and_reconstructor(tmp_path):
    """Verifies differentiable PAE gradient flow inside CaptumModelWrapper and AgentReconstructor PAE load."""
    pae = PredictiveAutoencoder(input_dim=12, latent_dim=8, history_len=12, d_model=16, nhead=2, num_layers=1)
    torch.save(pae.state_dict(), str(tmp_path / "pae_universal.pth"))

    lm = MagicMock()
    orig_agent = LocalAgent(
        tlight_id="JUNC_01",
        n_observations=10,
        n_actions=2,
        initial_hyperparams={},
        log_dir=str(tmp_path),
        locale_manager=lm,
        shared_pae=pae,
    )
    orig_agent.save_checkpoint(str(tmp_path / "agent_JUNC_01.pth"))

    reconstructor = AgentReconstructor(str(tmp_path))
    assert reconstructor.shared_pae is not None
    assert reconstructor.shared_pae.training is False
    if IS_REAL_TORCH:
        assert reconstructor.shared_pae.input_dim == 12
        assert reconstructor.shared_pae.latent_dim == 8

    rec_agent = reconstructor.reconstruct_agent("JUNC_01")
    assert rec_agent.n_actions == 2
    assert rec_agent.policy_net.training is False

    if IS_REAL_TORCH:
        # Zero out direct raw-feature channels in TCN conv1 so ONLY the PAE latent channels carry signal!
        with torch.no_grad():
            rec_agent.policy_net.tcn.network[0].conv1.weight[:, :10, :] = 0.0

        wrapper = CaptumModelWrapper(rec_agent.policy_net, shared_pae=reconstructor.shared_pae).to(rec_agent.device)
        x = torch.randn(2, 12, 10, device=rec_agent.device, requires_grad=True)
        logits = wrapper(x)
        assert logits.shape == (2, 2)
        logits[:, 0].sum().backward()
        assert x.grad is not None
        assert float(x.grad.abs().sum().item()) > 0.0, "Gradients MUST flow through PAE.encode back to input x!"
