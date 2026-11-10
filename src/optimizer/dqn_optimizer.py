# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Any, Callable, Dict, Optional

import torch
import torch.nn as nn
import torch.nn.functional as F


class DQNOptimizer:
    """
    Executes Off-Policy Distributional Dueling Double DQN (`QR-D3QN`) optimization
    with Quantile Huber Loss, Prioritized Experience Replay (PER), Polyak soft
    target updates, and automatic scalar SmoothL1 fallback for mock/legacy networks.
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
        self.gamma = float(hyperparams.get("gamma", 0.90))
        self.batch_size = int(hyperparams.get("batch_size", 128))
        self.tau = float(hyperparams.get("tau", 0.005))
        self.grad_clip_norm = float(hyperparams.get("grad_clip_norm", 1.0))

    @staticmethod
    def _resolve_quantile_callable(
        net: nn.Module, forward_fn: Callable, explicit_fn: Optional[Callable], method_name: str
    ) -> Optional[Callable]:
        if not isinstance(getattr(nn, "Linear", None), type):
            return None
        if explicit_fn is not None:
            return explicit_fn
        if getattr(net, "is_distributional", False) is not True:
            return None
        bound_owner = getattr(forward_fn, "__self__", None)
        if bound_owner is not None and hasattr(bound_owner, method_name):
            return getattr(bound_owner, method_name)
        return None

    def step(
        self,
        policy_net: nn.Module,
        target_net: nn.Module,
        optimizer: torch.optim.Optimizer,
        memory: Any,
        forward_policy: Callable,
        forward_target: Callable,
        forward_policy_quantiles: Optional[Callable] = None,
        forward_target_quantiles: Optional[Callable] = None,
    ) -> float:
        """
        Executes a Double DQN / QR-D3QN optimization step with PER importance-sampling weights.
        """
        if len(memory) < self.batch_size:
            return 0.0

        sample_result = memory.sample(self.batch_size)
        if sample_result is None:
            return 0.0

        state_batch, action_batch, next_states_batch, non_final_mask, reward_batch, indices, is_weights = sample_result
        non_final_next_states = next_states_batch[non_final_mask]

        fp_quantiles = self._resolve_quantile_callable(
            policy_net, forward_policy, forward_policy_quantiles, "forward_policy_quantiles"
        )
        ft_quantiles = self._resolve_quantile_callable(
            target_net, forward_target, forward_target_quantiles, "forward_target_quantiles"
        )
        use_qr_dqn = fp_quantiles is not None and ft_quantiles is not None

        if hasattr(policy_net, "train"):
            policy_net.train(True)

        try:
            optimizer.zero_grad()

            with torch.amp.autocast(device_type=self.device.type, enabled=self.scaler.is_enabled()):
                if use_qr_dqn and fp_quantiles is not None and ft_quantiles is not None:
                    # --- Distributional QR-D3QN with Quantile Huber Loss ---
                    curr_dist = fp_quantiles(state_batch)  # [B, n_actions, N]
                    num_quantiles = curr_dist.size(-1)
                    act_idx = action_batch.view(-1, 1, 1).expand(-1, 1, num_quantiles)
                    theta_i = curr_dist.gather(1, act_idx).squeeze(1).float()  # [B, N]

                    with torch.no_grad():
                        target_theta = reward_batch.float().view(-1, 1).expand(-1, num_quantiles).clone()
                        if non_final_mask.any():
                            next_policy_dist = fp_quantiles(non_final_next_states)
                            next_best_actions = next_policy_dist.mean(dim=-1).argmax(dim=1)
                            next_target_dist = ft_quantiles(non_final_next_states)
                            next_idx = next_best_actions.view(-1, 1, 1).expand(-1, 1, num_quantiles)
                            next_quantiles = next_target_dist.gather(1, next_idx).squeeze(1).float()
                            target_theta[non_final_mask] = (
                                reward_batch[non_final_mask].float().unsqueeze(1) + self.gamma * next_quantiles
                            )

                    # Pairwise Quantile Huber Loss: [B, N_curr, N_target]
                    theta_expanded = theta_i.unsqueeze(2).expand(-1, num_quantiles, num_quantiles)
                    target_expanded = target_theta.unsqueeze(1).expand(-1, num_quantiles, num_quantiles)
                    td_u = target_expanded - theta_expanded
                    huber_loss = F.smooth_l1_loss(theta_expanded, target_expanded, reduction="none")

                    taus = getattr(policy_net, "quantile_taus", None)
                    if taus is None or taus.numel() != num_quantiles:
                        taus = (torch.arange(num_quantiles, device=theta_i.device, dtype=torch.float32) + 0.5) / float(
                            num_quantiles
                        )
                    taus_view = taus.to(device=theta_i.device, dtype=torch.float32).view(1, num_quantiles, 1)
                    quantile_weights = torch.abs(taus_view - (td_u.detach() < 0.0).float())

                    per_sample_loss = (quantile_weights * huber_loss).sum(dim=1).mean(dim=1)  # [B]
                    loss = (per_sample_loss * is_weights.float().view(-1)).mean()
                    td_errors = torch.abs(theta_i.mean(dim=-1) - target_theta.mean(dim=-1)).detach().unsqueeze(1)
                else:
                    # --- Standard Double Dueling DQN Fallback ---
                    state_action_values = forward_policy(state_batch).gather(1, action_batch)
                    next_state_values = torch.zeros(self.batch_size, device=self.device)

                    with torch.no_grad():
                        if non_final_mask.any():
                            next_state_actions = forward_policy(non_final_next_states).max(1)[1].unsqueeze(1)
                            next_state_values[non_final_mask] = (
                                forward_target(non_final_next_states).gather(1, next_state_actions).squeeze(1).float()
                            )

                    expected_state_action_values = (next_state_values * self.gamma) + reward_batch
                    td_errors = torch.abs(state_action_values - expected_state_action_values.unsqueeze(1)).detach()

                    unweighted_loss = nn.SmoothL1Loss(reduction="none")(
                        state_action_values, expected_state_action_values.unsqueeze(1)
                    )
                    loss = (unweighted_loss * is_weights.unsqueeze(1)).mean()

            self.scaler.scale(loss).backward()
            self.scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(policy_net.parameters(), self.grad_clip_norm)
            self.scaler.step(optimizer)
            self.scaler.update()

            memory.update_priorities(indices, td_errors.squeeze(1))
        finally:
            if hasattr(policy_net, "train"):
                policy_net.train(False)

        return loss.item()

    def update_target_net(self, policy_net: nn.Module, target_net: nn.Module) -> None:
        """Hard override of target parameters from policy parameters."""
        target_net.load_state_dict(policy_net.state_dict())

    def soft_update_target_net(
        self, policy_net: nn.Module, target_net: nn.Module, tau: Optional[float] = None
    ) -> None:
        """Polyak soft target update: `theta_target <- tau * theta_policy + (1 - tau) * theta_target`."""
        blend = float(self.tau if tau is None else tau)
        if not isinstance(getattr(nn, "Linear", None), type):
            target_net.load_state_dict(policy_net.state_dict())
            return
        with torch.no_grad():
            for p_param, t_param in zip(policy_net.parameters(), target_net.parameters()):
                if isinstance(p_param, torch.Tensor) and isinstance(t_param, torch.Tensor):
                    t_param.data.mul_(1.0 - blend).add_(p_param.data, alpha=blend)
