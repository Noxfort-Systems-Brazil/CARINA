# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Distributional & Counterfactual Neural Spillback Predictor for Guardian Agent (SOLID: SRP & DIP).

Delegates physics projection, capacity-aware edge slicing, quantile spread calibration,
and non-compensatory Noisy-OR sensor fusion to `GuardianRiskCalibrator`.
"""

from collections import deque
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn

from src.models.pae import PredictiveAutoencoder
from src.safety.guardian_risk_calibrator import GuardianRiskCalibrator


class GuardianNeuralPredictor:
    """
    Manages temporal state sequences and delegates calibrated tail-risk predictions
    to `GuardianRiskCalibrator` using QR-D3QN CVaR margins, kinematic saturation,
    and Universal PAE counterfactual projections.
    """

    def __init__(
        self,
        policy_net: torch.nn.Module,
        target_net: Optional[torch.nn.Module],
        device: torch.device,
        shared_pae: Optional[PredictiveAutoencoder] = None,
        temporal_seq_len: int = 12,
        action_keep_stage: int = 0,
        calibration_temperature: float = 1.0,
        neural_weight: Optional[float] = None,
        cvar_alpha: float = 0.20,
        clearance_horizon_sec: float = 6.0,
        edge_feature_dim: Optional[int] = None,
        edge_capacities: Optional[List[float]] = None,
        calibrator: Optional[GuardianRiskCalibrator] = None,
    ):
        self.policy_net = policy_net
        self.target_net = target_net
        self.device = device
        self.shared_pae = shared_pae
        self.pae_latent_dim = shared_pae.latent_dim if shared_pae else 0
        self.temporal_seq_len = temporal_seq_len
        self.action_keep_stage = action_keep_stage
        self.calibration_temperature = max(float(calibration_temperature), 1e-3)
        self.neural_weight = float(np.clip(neural_weight, 0.0, 1.0)) if neural_weight is not None else 0.85
        self.cvar_alpha = float(np.clip(cvar_alpha, 0.05, 1.0))
        self.state_deques: Dict[str, deque] = {}

        self.calibrator = calibrator or GuardianRiskCalibrator(
            action_keep_stage=action_keep_stage,
            cvar_alpha=self.cvar_alpha,
            calibration_temperature=self.calibration_temperature,
            neural_weight=neural_weight,
            clearance_horizon_sec=clearance_horizon_sec,
            edge_feature_dim=edge_feature_dim,
            edge_capacities=edge_capacities,
        )

    def get_temporal_sequence(self, state: List[float], tl_id: str) -> torch.Tensor:
        """Manages the temporal deque for a `tl_id` and returns a batched sequence tensor."""
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

    def _extract_saturation_from_vector(self, vec: np.ndarray) -> float:
        return self.calibrator.extract_saturation(vec)

    def _compute_kinematic_risk(self, tl_id: str, fallback_state: List[float]) -> float:
        history = list(self.state_deques.get(tl_id, [fallback_state]))
        return self.calibrator.compute_kinematic_risk(history, fallback_state)

    def _compute_pae_forecast_risk(self, pae_latent: torch.Tensor, valid_dim: Optional[int] = None) -> Optional[float]:
        risk, _ = self.calibrator.compute_pae_forecast_risk(
            self.shared_pae, pae_latent, self.device, valid_dim=valid_dim
        )
        return risk

    def _compute_cvar_effective_q(self, q_quantiles: torch.Tensor) -> Tuple[torch.Tensor, float]:
        eff_q, cvar_margin, _ = self.calibrator.compute_cvar_effective_q(q_quantiles)
        return eff_q, cvar_margin

    def _compute_calibrated_neural_prob(self, q_values: Any) -> Tuple[float, float]:
        return self.calibrator.compute_neural_prob(q_values)

    def evaluate_spillback_breakdown(
        self, state: List[float], tl_id: str, precomputed_pae_latent: Optional[torch.Tensor] = None
    ) -> Dict[str, float]:
        """Evaluates calibrated spillback breakdown using Noisy-OR fusion across sensors."""
        seq_tensor = self.get_temporal_sequence(state, tl_id)
        device_type = self.device.type if hasattr(self, "device") and hasattr(self.device, "type") else "cpu"
        is_dist = (
            isinstance(getattr(nn, "Linear", None), type)
            and getattr(self.policy_net, "is_distributional", None) is True
            and callable(getattr(self.policy_net, "forward_quantiles", None))
        )

        cvar_margin = 0.0
        quantile_spread: Optional[float] = None
        with torch.no_grad(), torch.amp.autocast(device_type=device_type, enabled=(device_type == "cuda")):
            pae_latent = self.get_pae_latent(seq_tensor, precomputed_latent=precomputed_pae_latent)
            if is_dist:
                q_quantiles = self.policy_net.forward_quantiles(seq_tensor, pae_latent)  # type: ignore[operator]
                q_values, cvar_margin, quantile_spread = self.calibrator.compute_cvar_effective_q(q_quantiles)
            else:
                q_values = self.policy_net(seq_tensor, pae_latent)

        neural_prob, q_margin = self.calibrator.compute_neural_prob(
            q_values, cvar_margin=cvar_margin if is_dist else None, quantile_spread=quantile_spread
        )
        if not is_dist:
            cvar_margin = q_margin

        kinematic_risk = self._compute_kinematic_risk(tl_id, state)
        pae_risk, pae_rel = self.calibrator.compute_pae_forecast_risk(
            self.shared_pae, pae_latent, self.device, valid_dim=len(state)
        )
        fused_risk = self.calibrator.fuse_risks(
            kinematic_risk=kinematic_risk,
            neural_prob=neural_prob,
            pae_risk=pae_risk,
            pae_reliability=pae_rel,
        )

        return {
            "risk": fused_risk,
            "neural_prob": neural_prob,
            "kinematic_risk": kinematic_risk,
            "pae_risk": pae_risk if pae_risk is not None else kinematic_risk,
            "pae_reliability": pae_rel,
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
        net = self.target_net if self.target_net is not None else self.policy_net
        return net(states_batch, pae_latent)

    def forward_policy_quantiles(self, states_batch: torch.Tensor) -> torch.Tensor:
        pae_latent = self.get_pae_latent(states_batch)
        return self.policy_net.forward_quantiles(states_batch, pae_latent)  # type: ignore[operator]

    def forward_target_quantiles(self, states_batch: torch.Tensor) -> torch.Tensor:
        pae_latent = self.get_pae_latent(states_batch)
        net = self.target_net if self.target_net is not None else self.policy_net
        return net.forward_quantiles(states_batch, pae_latent)  # type: ignore[operator]
