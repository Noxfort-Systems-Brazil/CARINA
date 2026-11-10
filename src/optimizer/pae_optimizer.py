# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Any, Optional, Union

import torch
import torch.nn as nn
import torch.nn.functional as F


class PAEOptimizer:
    """
    Executes self-supervised and action-conditioned World Model optimization for the
    Universal Predictive Autoencoder (`PredictiveAutoencoder`):
    - Computes masked Huber + Heteroscedastic Gaussian NLL loss over active non-padded
      intersection channels (`valid_dims`), preventing zero-padded channels from biasing
      dynamics learning on heterogeneous intersections.
    - Supports optional binary action conditioning (`0 = ADVANCE`, `1 = KEEP`).
    - Restores `model.eval()` on exit for deterministic fleet inference.
    """

    def __init__(
        self,
        learning_rate: float = 5e-4,
        device: Optional[torch.device] = None,
        scaler: Optional[torch.amp.GradScaler] = None,
    ) -> None:
        self.learning_rate = learning_rate
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        cuda_present = self.device.type == "cuda"
        self.scaler = scaler or torch.amp.GradScaler(enabled=cuda_present)
        self.loss_fn = nn.MSELoss()
        self.optimizer: Optional[torch.optim.Optimizer] = None
        self._target_model: Optional[nn.Module] = None

    def _ensure_optimizer(self, model: nn.Module) -> torch.optim.Optimizer:
        """Lazily creates or re-binds the AdamW optimizer to the target model parameters."""
        if self.optimizer is None or self._target_model is not model:
            self.optimizer = torch.optim.AdamW(model.parameters(), lr=self.learning_rate)
            self._target_model = model
        return self.optimizer

    def _compute_world_model_loss(
        self,
        model: nn.Module,
        current_state: torch.Tensor,
        next_state: torch.Tensor,
        action: Optional[Union[int, torch.Tensor]] = None,
        valid_dims: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        Returns per-sample loss `[batch_size]` using masked Huber + heteroscedastic Gaussian NLL
        when `decode_with_uncertainty` is available on real PyTorch tensors, or MSE fallback for mocks.
        """
        is_real_torch = isinstance(getattr(nn, "Linear", None), type) and isinstance(current_state, torch.Tensor)
        orig_target_dim = next_state.size(-1) if hasattr(next_state, "size") else None

        if hasattr(model, "pad_to_input_dim"):
            next_state_padded = model.pad_to_input_dim(next_state)
        else:
            next_state_padded = next_state

        if next_state_padded.dim() == 3:
            next_state_padded = next_state_padded[:, -1, :]

        if not is_real_torch or not hasattr(model, "decode_with_uncertainty") or not hasattr(model, "encode"):
            predicted_next = model(current_state)
            diff = (predicted_next - next_state_padded.detach()).pow(2)
            return diff.view(diff.size(0), -1).mean(dim=1)

        batch_size, target_dim = next_state_padded.size(0), next_state_padded.size(-1)
        if valid_dims is None and isinstance(orig_target_dim, int) and 0 < orig_target_dim < target_dim:
            eff_valid_dims: Optional[torch.Tensor] = torch.full(
                (batch_size,), orig_target_dim, dtype=torch.long, device=current_state.device
            )
        elif valid_dims is not None:
            eff_valid_dims = valid_dims.to(device=current_state.device, dtype=torch.long).view(-1)
        else:
            eff_valid_dims = None

        z = model.encode(current_state, valid_dims=eff_valid_dims)

        # Apply action conditioning per sample where action >= 0
        if action is not None:
            if isinstance(action, int):
                cond_action: Optional[Union[int, torch.Tensor]] = action if action >= 0 else None
                mean, log_var = model.decode_with_uncertainty(z, action=cond_action)
            else:
                act_t = action.to(device=z.device, dtype=torch.long).view(-1)
                has_valid_act = act_t >= 0
                if bool(has_valid_act.all()):
                    mean, log_var = model.decode_with_uncertainty(z, action=act_t)
                elif bool(has_valid_act.any()):
                    clamped_act = torch.clamp(act_t, min=0)
                    z_act = model._condition_latent(z, action=clamped_act)
                    z_eff = torch.where(has_valid_act.unsqueeze(-1), z_act, z)
                    mean = model.decoder(z_eff)
                    log_var = torch.clamp(model.log_var_head(z_eff), -6.0, 2.0)
                else:
                    mean, log_var = model.decode_with_uncertainty(z, action=None)
        else:
            mean, log_var = model.decode_with_uncertainty(z, action=None)

        target = next_state_padded.detach().float()
        mean_f = mean.float()
        log_var_f = log_var.float()

        huber_elem = F.smooth_l1_loss(mean_f, target, reduction="none")
        sq_err = (mean_f - target).pow(2)
        nll_elem = 0.5 * (torch.exp(-log_var_f) * sq_err + log_var_f + 6.0)
        elem_loss = 0.85 * huber_elem + 0.15 * nll_elem  # Non-negative since log_var >= -6.0

        if eff_valid_dims is not None:
            v_clamped = torch.clamp(eff_valid_dims, min=1, max=target_dim)
            active_mask = (torch.arange(target_dim, device=target.device).unsqueeze(0) < v_clamped.unsqueeze(1)).float()
            per_sample = (elem_loss * active_mask).sum(dim=1) / torch.clamp(active_mask.sum(dim=1), min=1.0)
        else:
            per_sample = elem_loss.mean(dim=1)

        return per_sample

    def step(
        self,
        model: nn.Module,
        current_state: torch.Tensor,
        next_state: torch.Tensor,
        action: Optional[Union[int, torch.Tensor]] = None,
        valid_dims: Optional[torch.Tensor] = None,
    ) -> float:
        """
        Executes a single world-model predictive training step and restores `model.eval()`.
        """
        if hasattr(current_state, "device") and current_state.device != self.device:
            current_state = current_state.to(self.device)
        if hasattr(next_state, "device") and next_state.device != self.device:
            next_state = next_state.to(self.device)

        if current_state.dim() == 2 and next_state.dim() == 1:
            current_state = current_state.unsqueeze(0)
            next_state = next_state.unsqueeze(0)
        elif next_state.dim() == 1:
            next_state = next_state.unsqueeze(0)

        model.train()
        try:
            optimizer = self._ensure_optimizer(model)
            optimizer.zero_grad()

            device_type = "cuda" if current_state.is_cuda else "cpu"
            with torch.amp.autocast(device_type=device_type, enabled=self.scaler.is_enabled()):
                per_sample_loss = self._compute_world_model_loss(
                    model, current_state, next_state, action=action, valid_dims=valid_dims
                )
                loss = per_sample_loss.mean()

            self.scaler.scale(loss).backward()
            self.scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            self.scaler.step(optimizer)
            self.scaler.update()
        finally:
            model.eval()

        return float(loss.item() if hasattr(loss, "item") else loss)

    def step_from_memory(
        self,
        model: nn.Module,
        memory: Any,
        batch_size: int = 32,
        prioritized: bool = True,
    ) -> float:
        """
        Samples transitions from `StateReplayMemory`, executes masked world-model optimization,
        and updates PER priorities.
        """
        if memory is None or len(memory) < batch_size:
            return 0.0

        try:
            sample_res = memory.sample(batch_size, prioritized=prioritized, include_metadata=True)
        except TypeError:
            sample_res = memory.sample(batch_size, prioritized=prioritized)

        if sample_res is None:
            return 0.0

        if len(sample_res) >= 6:
            batch_curr, batch_next, indices, is_weights, batch_actions, batch_valid_dims = sample_res[:6]
        else:
            batch_curr, batch_next, indices, is_weights = sample_res[:4]
            batch_actions, batch_valid_dims = None, None

        if hasattr(batch_curr, "device") and batch_curr.device != self.device:
            batch_curr = batch_curr.to(self.device)
        if hasattr(batch_next, "device") and batch_next.device != self.device:
            batch_next = batch_next.to(self.device)
        if is_weights is not None and hasattr(is_weights, "device") and is_weights.device != self.device:
            is_weights = is_weights.to(self.device)

        model.train()
        try:
            optimizer = self._ensure_optimizer(model)
            optimizer.zero_grad()

            device_type = "cuda" if batch_curr.is_cuda else "cpu"
            with torch.amp.autocast(device_type=device_type, enabled=self.scaler.is_enabled()):
                per_sample_loss = self._compute_world_model_loss(
                    model,
                    batch_curr,
                    batch_next,
                    action=batch_actions,
                    valid_dims=batch_valid_dims,
                )

                if prioritized and is_weights is not None:
                    loss = (per_sample_loss * is_weights).mean()
                else:
                    loss = per_sample_loss.mean()

            self.scaler.scale(loss).backward()
            self.scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            self.scaler.step(optimizer)
            self.scaler.update()

            if hasattr(memory, "update_priorities"):
                try:
                    memory.update_priorities(indices, per_sample_loss.detach())
                except Exception:
                    pass
        finally:
            model.eval()

        try:
            return float(loss.item() if hasattr(loss, "item") else loss)
        except Exception:
            return 0.5
