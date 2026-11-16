# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Any, Callable, Dict, Optional, Sequence, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


class PPOOptimizer:
    """
    Executes Proximal Policy Optimization (PPO) with:
    - Exact GAE(lambda) bootstrap via `last_next_value` (non-terminal horizon accuracy).
    - Shuffled mini-batching (`minibatch_size`) across `k_epochs`.
    - Value Function Clipping + Huber (`SmoothL1Loss`) to shield against traffic shock outliers.
    - Schulman's non-negative approximate KL estimator `(r - 1) - log(r)` for reliable early stopping.
    - Explicit `.train(True)` -> `.train(False)` discipline so inference never leaks Dropout.
    """

    def __init__(
        self, hyperparams: Dict[str, Any], device: torch.device, scaler: Optional[torch.amp.GradScaler] = None
    ) -> None:
        self.device = device
        cuda_present = self.device.type == "cuda"
        self.scaler = scaler or torch.amp.GradScaler(enabled=cuda_present)
        self.load_hyperparameters(hyperparams)

    def load_hyperparameters(self, hyperparams: Dict[str, Any]) -> None:
        """Updates internal RL hyperparameters without destroying the object."""
        self.gamma = float(hyperparams.get("gamma", 0.99))
        self.gae_lambda = float(hyperparams.get("gae_lambda", 0.95))
        self.eps_clip = float(hyperparams.get("eps_clip", 0.2))
        self.k_epochs = int(hyperparams.get("k_epochs", 4))
        self.target_kl = float(hyperparams.get("target_kl", 0.02))
        self.grad_clip_norm = float(hyperparams.get("grad_clip_norm", 0.5))
        self.critic_loss_coef = float(hyperparams.get("critic_loss_coef", 0.5))
        self.entropy_coef = float(hyperparams.get("entropy_coef", 0.01))
        self.minibatch_size = max(1, int(hyperparams.get("minibatch_size", 64)))
        self.clip_vloss = bool(hyperparams.get("clip_vloss", True))

    def step(
        self,
        policy_net: nn.Module,
        optimizer: torch.optim.Optimizer,
        memory_batch: Sequence[Any],
        evaluate_fn: Callable,
        last_next_value: Optional[float] = None,
        precomputed_latents: Optional[torch.Tensor] = None,
    ) -> float:
        """
        Executes PPO optimization epochs over `memory_batch`.

        Supports both 6-tuple `(old_states, old_actions, old_log_probs, rewards, dones, old_state_values)`
        and 7-tuple `(..., bootstrap_next_value)`.
        """
        if len(memory_batch) >= 7 and last_next_value is None:
            old_states, old_actions, old_log_probs, rewards, dones, old_state_values, bootstrap_val = memory_batch[:7]
            if bootstrap_val is not None:
                last_next_value = float(bootstrap_val.item() if hasattr(bootstrap_val, "item") else bootstrap_val)
        else:
            old_states, old_actions, old_log_probs, rewards, dones, old_state_values = memory_batch[:6]

        if len(rewards) == 0:
            return 0.0

        is_real_torch = isinstance(getattr(nn, "Linear", None), type) and isinstance(old_state_values, torch.Tensor)

        # Extract CPU state values before migrating tensors so GAE runs in pure host NumPy without GPU micro-kernels
        if is_real_torch:
            vals_cpu_np = old_state_values.detach().float().cpu().numpy().reshape(-1)
        else:
            vals_cpu_np = None

        if hasattr(old_states, "to"):
            old_states = old_states.to(self.device)
        if hasattr(old_actions, "to"):
            old_actions = old_actions.to(self.device)
        if hasattr(old_log_probs, "to"):
            old_log_probs = old_log_probs.to(self.device)
        if hasattr(old_state_values, "to"):
            old_state_values = old_state_values.to(self.device)

        # 1. Generalized Advantage Estimation (GAE) with exact terminal/bootstrap value
        with torch.no_grad():
            n_steps = len(rewards)
            if is_real_torch and vals_cpu_np is not None:
                bootstrap_val = float(last_next_value) if last_next_value is not None else float(vals_cpu_np[-1])
                rewards_np = np.asarray(rewards, dtype=np.float32)
                non_term_np = 1.0 - np.asarray(dones, dtype=np.float32)
                adv_np = np.zeros(n_steps, dtype=np.float32)
                gae_f = 0.0
                gamma = self.gamma
                lam = self.gae_lambda
                for t in range(n_steps - 1, -1, -1):
                    nt = float(non_term_np[t])
                    next_v = float(vals_cpu_np[t + 1]) if t < n_steps - 1 else bootstrap_val
                    delta_f = float(rewards_np[t]) + gamma * next_v * nt - float(vals_cpu_np[t])
                    gae_f = delta_f + gamma * lam * nt * gae_f
                    adv_np[t] = gae_f
                advantages = torch.from_numpy(adv_np).to(self.device)
            else:
                if last_next_value is not None:
                    bootstrap_v: Any = torch.tensor(float(last_next_value), dtype=torch.float32, device=self.device)
                else:
                    bootstrap_v = old_state_values[-1]

                advantages = torch.zeros_like(torch.tensor(rewards, dtype=torch.float32), dtype=torch.float32).to(
                    self.device
                )
                gae: Any = 0.0
                for t in reversed(range(n_steps)):
                    non_terminal = 1.0 - float(dones[t])
                    next_value = old_state_values[t + 1] if t < n_steps - 1 else bootstrap_v
                    delta = rewards[t] + self.gamma * next_value * non_terminal - old_state_values[t]
                    gae = delta + self.gamma * self.gae_lambda * non_terminal * gae
                    advantages[t] = gae

            rewards_to_go = advantages + old_state_values
            advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        total_loss_val = 0.0
        n_samples = len(rewards)
        use_minibatches = is_real_torch and isinstance(old_states, torch.Tensor) and n_samples > self.minibatch_size

        if hasattr(policy_net, "train"):
            policy_net.train(True)

        try:
            for _ in range(self.k_epochs):
                epoch_kl_sum = 0.0
                mb_count = 0

                if use_minibatches:
                    perm = torch.randperm(n_samples, device=self.device)
                    slices = [
                        perm[start : start + self.minibatch_size] for start in range(0, n_samples, self.minibatch_size)
                    ]
                else:
                    slices = [None]

                for mb_idx in slices:
                    if mb_idx is None:
                        mb_states = old_states
                        mb_actions = old_actions
                        mb_old_log_probs = old_log_probs
                        mb_old_values = old_state_values
                        mb_adv = advantages
                        mb_returns = rewards_to_go
                    else:
                        mb_states = old_states[mb_idx]
                        mb_actions = old_actions[mb_idx]
                        mb_old_log_probs = old_log_probs[mb_idx]
                        mb_old_values = old_state_values[mb_idx]
                        mb_adv = advantages[mb_idx]
                        if mb_adv.numel() > 1:
                            mb_adv = (mb_adv - mb_adv.mean()) / (mb_adv.std() + 1e-8)
                        mb_returns = rewards_to_go[mb_idx]

                    mb_latents = (
                        precomputed_latents[mb_idx]
                        if (precomputed_latents is not None and mb_idx is not None)
                        else precomputed_latents
                    )

                    optimizer.zero_grad()

                    with torch.amp.autocast(device_type=self.device.type, enabled=self.scaler.is_enabled()):
                        if mb_latents is not None:
                            new_log_probs, state_values, dist_entropy = evaluate_fn(
                                mb_states, mb_actions, precomputed_pae_latent=mb_latents
                            )
                        else:
                            new_log_probs, state_values, dist_entropy = evaluate_fn(mb_states, mb_actions)

                        if is_real_torch and isinstance(new_log_probs, torch.Tensor):
                            dev = new_log_probs.device
                            old_lp_d = mb_old_log_probs.detach().to(dev).view(-1)
                            adv_d = mb_adv.to(dev).view(-1)
                            ret_d = mb_returns.detach().to(dev).view(-1)

                            log_ratios = new_log_probs.view(-1) - old_lp_d
                            ratios = torch.exp(torch.clamp(log_ratios, -20.0, 20.0))

                            surr1 = ratios * adv_d
                            surr2 = torch.clamp(ratios, 1.0 - self.eps_clip, 1.0 + self.eps_clip) * adv_d
                            actor_loss = -torch.min(surr1, surr2).mean()

                            v_pred = state_values.view(-1)
                            v_loss_unclipped = F.smooth_l1_loss(v_pred, ret_d, reduction="none")
                            if self.clip_vloss:
                                v_old = mb_old_values.detach().to(dev).view(-1)
                                v_clipped = v_old + torch.clamp(v_pred - v_old, -self.eps_clip, self.eps_clip)
                                v_loss_clipped = F.smooth_l1_loss(v_clipped, ret_d, reduction="none")
                                critic_loss = torch.maximum(v_loss_unclipped, v_loss_clipped).mean()
                            else:
                                critic_loss = v_loss_unclipped.mean()

                            entropy_bonus = -self.entropy_coef * dist_entropy.mean()
                            total_loss = actor_loss + (self.critic_loss_coef * critic_loss) + entropy_bonus
                        else:
                            ratios = torch.exp(new_log_probs - mb_old_log_probs.detach())
                            surr1 = ratios * mb_adv
                            surr2 = torch.clamp(ratios, 1.0 - self.eps_clip, 1.0 + self.eps_clip) * mb_adv
                            actor_loss = -torch.min(surr1, surr2).mean()
                            critic_loss = nn.SmoothL1Loss()(state_values, mb_returns.detach())
                            entropy_bonus = -self.entropy_coef * dist_entropy.mean()
                            total_loss = actor_loss + (self.critic_loss_coef * critic_loss) + entropy_bonus

                    self.scaler.scale(total_loss).backward()
                    self.scaler.unscale_(optimizer)
                    torch.nn.utils.clip_grad_norm_(policy_net.parameters(), self.grad_clip_norm)
                    self.scaler.step(optimizer)
                    self.scaler.update()

                    total_loss_val = total_loss.item()

                    with torch.no_grad():
                        if is_real_torch and isinstance(new_log_probs, torch.Tensor):
                            lr_det = new_log_probs.detach().view(-1) - mb_old_log_probs.detach().view(-1)
                            r_det = torch.exp(torch.clamp(lr_det, -20.0, 20.0))
                            mb_kl = float(((r_det - 1.0) - lr_det).mean().item())
                        else:
                            kl_raw = torch.mean(mb_old_log_probs.detach() - new_log_probs).item()
                            mb_kl = abs(float(kl_raw)) if isinstance(kl_raw, (int, float)) else 0.0
                        epoch_kl_sum += mb_kl
                        mb_count += 1

                avg_kl = epoch_kl_sum / max(1, mb_count)
                if avg_kl > 1.5 * self.target_kl:
                    break
        finally:
            if hasattr(policy_net, "train"):
                policy_net.train(False)

        return total_loss_val
