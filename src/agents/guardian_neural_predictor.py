# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Distributional & Counterfactual Neural Spillback Predictor for Guardian Agent (SOLID: SRP & DIP).

Combines:
1. Distributional QR-D3QN tail-risk evaluation via Conditional Value-at-Risk (`CVaR_alpha`),
   capturing worst-case gridlock/spillback quantiles rather than mean Q-values alone.
2. Action-conditioned counterfactual PAE forecasts (`decode_with_uncertainty` for `ADVANCE` vs `KEEP`).
3. Kinematic queue/occupancy saturation and growth rates.
"""

from collections import deque
import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn

from src.models.pae import PredictiveAutoencoder


class GuardianNeuralPredictor:
    """
    Manages temporal state sequences and calibrated tail-risk predictions
    for physical spillback using QR-D3QN CVaR margins, kinematic saturation,
    and Universal PAE counterfactual projections.
    """

    def __init__(
        self,
        policy_net: torch.nn.Module,
        target_net: torch.nn.Module,
        device: torch.device,
        shared_pae: Optional[PredictiveAutoencoder] = None,
        temporal_seq_len: int = 12,
        action_keep_stage: int = 0,
        calibration_temperature: float = 1.0,
        neural_weight: float = 0.65,
        cvar_alpha: float = 0.20,
    ):
        self.policy_net = policy_net
        self.target_net = target_net
        self.device = device
        self.shared_pae = shared_pae
        self.pae_latent_dim = shared_pae.latent_dim if shared_pae else 0
        self.temporal_seq_len = temporal_seq_len
        self.action_keep_stage = action_keep_stage
        self.calibration_temperature = max(float(calibration_temperature), 1e-3)
        self.neural_weight = float(np.clip(neural_weight, 0.0, 1.0))
        self.cvar_alpha = float(np.clip(cvar_alpha, 0.05, 1.0))
        self.state_deques: Dict[str, deque] = {}

    def get_temporal_sequence(self, state: List[float], tl_id: str) -> torch.Tensor:
        """
        Manages the temporal deque for a specific `tl_id` and returns
        the standardized temporal sequence as a tensor.
        """
        if tl_id not in self.state_deques:
            self.state_deques[tl_id] = deque(maxlen=self.temporal_seq_len)

        self.state_deques[tl_id].append(state)

        seq = list(self.state_deques[tl_id])
        while len(seq) < self.temporal_seq_len:
            seq.insert(0, seq[0])

        seq_np = np.array(seq, dtype=np.float32)
        return torch.from_numpy(seq_np).unsqueeze(0).to(self.device)

    def get_pae_latent(
        self, seq_tensor: torch.Tensor, precomputed_latent: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """Projects the state sequence into PAE latent space or reuses precomputed latent."""
        if precomputed_latent is not None:
            latent = precomputed_latent
            if hasattr(latent, "to") and hasattr(latent, "device") and latent.device != self.device:
                latent = latent.to(self.device)
            return latent

        if self.shared_pae is not None:
            with torch.no_grad():
                latent = self.shared_pae.encode(seq_tensor)
                if hasattr(latent, "to") and hasattr(latent, "device") and latent.device != self.device:
                    latent = latent.to(self.device)
                return latent
        return torch.zeros(seq_tensor.size(0), self.pae_latent_dim, device=self.device)

    @staticmethod
    def _extract_saturation_from_vector(vec: np.ndarray) -> float:
        """
        Extracts peak physical saturation (occupancy and queue ratio) in `[0.0, 1.0]`
        from a normalized state vector.
        """
        if vec.size == 0:
            return 0.0
        clipped = np.clip(vec.astype(np.float32), 0.0, 1.0)
        dim = clipped.size
        if dim >= 4:
            n_edge_feats = (dim // 3) * 3
            edge_slice = clipped[:n_edge_feats]
            if edge_slice.size >= 3:
                occupancies = edge_slice[0::3]
                queues = edge_slice[2::3]
                return float(np.clip(0.55 * np.max(occupancies) + 0.45 * np.max(queues), 0.0, 1.0))
        return float(np.max(clipped))

    def _compute_kinematic_risk(self, tl_id: str, fallback_state: List[float]) -> float:
        """
        Computes physical kinematic spillback risk in `[0.0, 1.0]` from current
        saturation and temporal queue/occupancy growth rate over the window.
        """
        history = list(self.state_deques.get(tl_id, [fallback_state]))
        if not history:
            return 0.0
        curr_vec = np.asarray(history[-1], dtype=np.float32).reshape(-1)
        first_vec = np.asarray(history[0], dtype=np.float32).reshape(-1)

        curr_sat = self._extract_saturation_from_vector(curr_vec)
        first_sat = self._extract_saturation_from_vector(first_vec) if first_vec.size == curr_vec.size else curr_sat
        growth_rate = max(0.0, curr_sat - first_sat)

        return float(np.clip(0.75 * curr_sat + 0.25 * growth_rate, 0.0, 1.0))

    def _compute_pae_forecast_risk(self, pae_latent: torch.Tensor, valid_dim: Optional[int] = None) -> Optional[float]:
        """
        Uses the Action-Conditioned Universal PAE World Model to evaluate counterfactual
        next-step spillback risk (comparing `0 = ADVANCE` vs `1 = KEEP` + epistemic uncertainty).
        """
        if self.shared_pae is None or not hasattr(self.shared_pae, "decode"):
            return None
        try:
            device_type = self.device.type if hasattr(self, "device") and hasattr(self.device, "type") else "cpu"
            is_real_torch = isinstance(getattr(nn, "Linear", None), type)
            with torch.no_grad(), torch.amp.autocast(device_type=device_type, enabled=(device_type == "cuda")):
                if is_real_torch and hasattr(self.shared_pae, "decode_with_uncertainty"):
                    mean_adv, logv_adv = self.shared_pae.decode_with_uncertainty(pae_latent, action=0)
                    mean_keep, _ = self.shared_pae.decode_with_uncertainty(pae_latent, action=1)
                    if isinstance(mean_adv, torch.Tensor) and isinstance(logv_adv, torch.Tensor):
                        std_adv = torch.exp(0.5 * logv_adv)
                        ucb_adv = (mean_adv.float() + 0.5 * std_adv.float()).detach().cpu().numpy().reshape(-1)
                        keep_np = mean_keep.float().detach().cpu().numpy().reshape(-1)
                        if valid_dim is not None and valid_dim > 0:
                            ucb_adv = ucb_adv[:valid_dim]
                            keep_np = keep_np[:valid_dim]
                        sat_adv = self._extract_saturation_from_vector(ucb_adv)
                        sat_keep = self._extract_saturation_from_vector(keep_np)
                        delta_spillback = max(0.0, sat_adv - sat_keep)
                        return float(np.clip(0.80 * sat_adv + 0.20 * delta_spillback, 0.0, 1.0))

                predicted_next = self.shared_pae.decode(pae_latent)
                if isinstance(predicted_next, torch.Tensor):
                    pred_np = predicted_next.detach().cpu().float().numpy().reshape(-1)
                    if valid_dim is not None and valid_dim > 0:
                        pred_np = pred_np[:valid_dim]
                    return self._extract_saturation_from_vector(pred_np)
        except Exception:
            return None
        return None

    def _compute_cvar_effective_q(self, q_quantiles: torch.Tensor) -> Tuple[torch.Tensor, float]:
        """
        Computes CVaR-blended effective Q-values `[B, n_actions]` from `[B, n_actions, N]`.
        Returns `(effective_q, cvar_margin)`.
        """
        sorted_q, _ = torch.sort(q_quantiles.float(), dim=-1)
        num_q = sorted_q.size(-1)
        k_tail = max(1, int(math.ceil(self.cvar_alpha * num_q)))
        cvar_q = sorted_q[..., :k_tail].mean(dim=-1)
        mean_q = sorted_q.mean(dim=-1)
        effective_q = 0.65 * cvar_q + 0.35 * mean_q

        keep_idx = self.action_keep_stage
        change_idx = 1 if keep_idx == 0 else 0
        cvar_margin = float((cvar_q[0, keep_idx] - cvar_q[0, change_idx]).item())
        return effective_q, cvar_margin

    def _compute_calibrated_neural_prob(self, q_values: Any) -> Tuple[float, float]:
        """
        Converts Q-values into a temperature-calibrated spillback probability:
            `P(spillback) = sigmoid((Q(s, KEEP) - Q(s, CHANGE)) / tau)`
        """
        q_arr: Optional[np.ndarray] = None
        if hasattr(q_values, "_data") and isinstance(getattr(q_values, "_data", None), (list, tuple, np.ndarray)):
            q_arr = np.asarray(q_values._data, dtype=np.float32).reshape(-1)
        elif isinstance(q_values, np.ndarray):
            q_arr = q_values.astype(np.float32).reshape(-1)
        elif isinstance(q_values, (list, tuple)):
            q_arr = np.asarray(q_values, dtype=np.float32).reshape(-1)
        elif isinstance(q_values, torch.Tensor):
            q_arr = q_values.detach().cpu().numpy().astype(np.float32).reshape(-1)

        if q_arr is not None and q_arr.size >= 2:
            keep_idx = self.action_keep_stage
            change_idx = 1 if keep_idx == 0 else 0
            q_margin = float(q_arr[keep_idx] - q_arr[change_idx])
            scaled_logit = float(np.clip(q_margin / self.calibration_temperature, -20.0, 20.0))
            prob = float(1.0 / (1.0 + np.exp(-scaled_logit)))
            return prob, q_margin

        if hasattr(q_values, "max"):
            neural_action = q_values.max(1)[1].item()
            if neural_action == self.action_keep_stage:
                return 1.0, 5.0
            return 0.0, -5.0

        return 0.0, 0.0

    def evaluate_spillback_breakdown(
        self, state: List[float], tl_id: str, precomputed_pae_latent: Optional[torch.Tensor] = None
    ) -> Dict[str, float]:
        """
        Evaluates and returns the calibrated spillback risk breakdown:
        - `neural_prob`: Temperature-scaled logistic advantage probability (using CVaR on QR-D3QN)
        - `kinematic_risk`: Instantaneous saturation + temporal queue growth rate
        - `pae_risk`: Counterfactual PAE next-step saturation (`ADVANCE` vs `KEEP`)
        - `cvar_margin`: Worst-tail quantile margin `CVaR(KEEP) - CVaR(CHANGE)`
        - `risk`: Calibrated fused continuous risk score in `[0.0, 1.0]`
        """
        seq_tensor = self.get_temporal_sequence(state, tl_id)
        device_type = self.device.type if hasattr(self, "device") and hasattr(self.device, "type") else "cpu"
        is_dist = (
            isinstance(getattr(nn, "Linear", None), type)
            and getattr(self.policy_net, "is_distributional", None) is True
            and callable(getattr(self.policy_net, "forward_quantiles", None))
        )

        cvar_margin = 0.0
        with torch.no_grad(), torch.amp.autocast(device_type=device_type, enabled=(device_type == "cuda")):
            pae_latent = self.get_pae_latent(seq_tensor, precomputed_latent=precomputed_pae_latent)
            if is_dist:
                q_quantiles = self.policy_net.forward_quantiles(seq_tensor, pae_latent)  # type: ignore[operator]
                q_values, cvar_margin = self._compute_cvar_effective_q(q_quantiles)
            else:
                q_values = self.policy_net(seq_tensor, pae_latent)

        neural_prob, q_margin = self._compute_calibrated_neural_prob(q_values)
        if not is_dist:
            cvar_margin = q_margin

        kinematic_risk = self._compute_kinematic_risk(tl_id, state)
        pae_risk = self._compute_pae_forecast_risk(pae_latent, valid_dim=len(state))

        if pae_risk is not None:
            physical_risk = 0.60 * kinematic_risk + 0.40 * pae_risk
        else:
            physical_risk = kinematic_risk

        fused_risk = float(
            np.clip(
                self.neural_weight * neural_prob + (1.0 - self.neural_weight) * physical_risk,
                0.0,
                1.0,
            )
        )

        return {
            "risk": fused_risk,
            "neural_prob": neural_prob,
            "kinematic_risk": kinematic_risk,
            "pae_risk": pae_risk if pae_risk is not None else kinematic_risk,
            "q_margin": q_margin,
            "cvar_margin": cvar_margin,
        }

    def evaluate_spillback_risk(
        self, state: List[float], tl_id: str, precomputed_pae_latent: Optional[torch.Tensor] = None
    ) -> float:
        return self.evaluate_spillback_breakdown(state, tl_id, precomputed_pae_latent=precomputed_pae_latent)["risk"]

    def forward_policy(self, states_batch: torch.Tensor) -> torch.Tensor:
        pae_latent = self.get_pae_latent(states_batch)
        return self.policy_net(states_batch, pae_latent)

    def forward_target(self, states_batch: torch.Tensor) -> torch.Tensor:
        pae_latent = self.get_pae_latent(states_batch)
        return self.target_net(states_batch, pae_latent)

    def forward_policy_quantiles(self, states_batch: torch.Tensor) -> torch.Tensor:
        pae_latent = self.get_pae_latent(states_batch)
        return self.policy_net.forward_quantiles(states_batch, pae_latent)  # type: ignore[operator]

    def forward_target_quantiles(self, states_batch: torch.Tensor) -> torch.Tensor:
        pae_latent = self.get_pae_latent(states_batch)
        return self.target_net.forward_quantiles(states_batch, pae_latent)  # type: ignore[operator]
