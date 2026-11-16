# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Scale-Invariant Risk Calibrator & Non-Compensatory Sensor Fusion for GuardianAgent.

Eliminates hardcoded fusion weights (`0.65/0.35`, `0.60/0.40`, `0.75/0.25`, `0.55/0.45`)
by delegating capacity-aware physical projection to `GuardianPhysicsEstimator`,
calibrating QR-D3QN quantile spreads on `CHILD` graduation with F2 threshold tuning,
and combining risk detectors via reliability-weighted Noisy-OR fusion.
"""

import math
from collections import deque
from typing import Any, Deque, Dict, List, Optional, Tuple

import numpy as np
import torch

from src.safety.guardian_physics_estimator import GuardianPhysicsEstimator


class GuardianRiskCalibrator:
    """Calibrates QR-D3QN outputs and fuses physical, PAE, and neural spillback risks."""

    MAX_OBSERVATIONS = 4096
    CROMWELL_CAP = 0.999

    def __init__(
        self,
        action_keep_stage: int = 0,
        cvar_alpha: float = 0.20,
        calibration_temperature: float = 1.0,
        neural_weight: Optional[float] = None,
        spillback_floor: float = 0.80,
        clearance_horizon_sec: float = 6.0,
        step_dt_sec: float = 0.25,
        edge_feature_dim: Optional[int] = None,
        edge_capacities: Optional[List[float]] = None,
    ) -> None:
        self.action_keep_stage = int(action_keep_stage)
        self.cvar_alpha = float(np.clip(cvar_alpha, 0.05, 1.0))
        self.calibration_temperature = max(float(calibration_temperature), 1e-3)
        self.legacy_neural_weight = float(np.clip(neural_weight, 0.0, 1.0)) if neural_weight is not None else None
        self.spillback_floor = float(np.clip(spillback_floor, 0.50, 0.95))

        self.physics = GuardianPhysicsEstimator(
            edge_feature_dim=edge_feature_dim,
            edge_capacities=edge_capacities,
            clearance_horizon_sec=clearance_horizon_sec,
            step_dt_sec=step_dt_sec,
        )

        # Lifecycle calibration & reliability state
        self.is_calibrated: bool = False
        self.is_frozen: bool = False
        self.child_learning_active: bool = False
        self.logit_scale: float = 1.0 / self.calibration_temperature
        self.logit_bias: float = 0.0
        self.reference_spread: float = 1.0
        self.calibrated_threshold: Optional[float] = None
        self.d3qn_reliability: float = self.legacy_neural_weight if self.legacy_neural_weight is not None else 0.85

        self.child_observations: Deque[Tuple[float, float, int]] = deque(maxlen=self.MAX_OBSERVATIONS)
        self.td_losses: Deque[float] = deque(maxlen=256)

    @property
    def edge_feature_dim(self) -> Optional[int]:
        return self.physics.edge_feature_dim

    @edge_feature_dim.setter
    def edge_feature_dim(self, value: Optional[int]) -> None:
        self.physics.edge_feature_dim = int(value) if value is not None and value >= 3 else None

    @property
    def edge_capacities(self) -> List[float]:
        return self.physics.edge_capacities

    @edge_capacities.setter
    def edge_capacities(self, value: Optional[List[float]]) -> None:
        self.physics.edge_capacities = [max(1.0, float(c)) for c in value] if value else []

    @property
    def clearance_horizon_sec(self) -> float:
        return self.physics.clearance_horizon_sec

    @clearance_horizon_sec.setter
    def clearance_horizon_sec(self, value: float) -> None:
        self.physics.clearance_horizon_sec = max(0.5, float(value))

    @property
    def latest_pae_mse(self) -> Optional[float]:
        return self.physics.latest_pae_mse

    @latest_pae_mse.setter
    def latest_pae_mse(self, value: Optional[float]) -> None:
        self.physics.latest_pae_mse = value

    def configure_topology(
        self,
        edge_feature_dim: Optional[int] = None,
        edge_capacities: Optional[List[float]] = None,
        clearance_horizon_sec: Optional[float] = None,
    ) -> None:
        self.physics.configure_topology(edge_feature_dim, edge_capacities, clearance_horizon_sec)

    def extract_saturation(
        self, vec: np.ndarray, edge_feature_dim: Optional[int] = None, edge_capacities: Optional[List[float]] = None
    ) -> float:
        return self.physics.extract_saturation(vec, edge_feature_dim, edge_capacities)

    def compute_kinematic_risk(self, history: List[Any], fallback_state: List[float]) -> float:
        return self.physics.compute_kinematic_risk(history, fallback_state)

    def compute_pae_reliability(self, pae_mse: Optional[float], log_var_mean: Optional[float]) -> float:
        return self.physics.compute_pae_reliability(pae_mse, log_var_mean)

    def compute_pae_forecast_risk(
        self, shared_pae: Any, pae_latent: torch.Tensor, device: Any, valid_dim: Optional[int] = None
    ) -> Tuple[Optional[float], float]:
        return self.physics.compute_pae_forecast_risk(shared_pae, pae_latent, device, valid_dim)

    def compute_cvar_effective_q(self, q_quantiles: torch.Tensor) -> Tuple[torch.Tensor, float, float]:
        """Computes CVaR-blended effective Q-values `[B, 2]`, `cvar_margin`, and IQR quantile spread."""
        sorted_q, _ = torch.sort(q_quantiles.float(), dim=-1)
        num_q = sorted_q.size(-1)
        k_tail = max(1, int(math.ceil(self.cvar_alpha * num_q)))
        cvar_q = sorted_q[..., :k_tail].mean(dim=-1)
        effective_q = 0.65 * cvar_q + 0.35 * sorted_q.mean(dim=-1)

        keep_idx = self.action_keep_stage
        change_idx = 1 if keep_idx == 0 else 0
        cvar_margin = float((cvar_q[0, keep_idx] - cvar_q[0, change_idx]).item())

        q25 = sorted_q[0, :, max(0, (num_q - 1) // 4)]
        q75 = sorted_q[0, :, min(num_q - 1, (3 * (num_q - 1)) // 4)]
        iqr_spread = float(torch.max(q75 - q25).item())
        return effective_q, cvar_margin, max(iqr_spread, 1e-3)

    def compute_neural_prob(
        self, q_values: Any, cvar_margin: Optional[float] = None, quantile_spread: Optional[float] = None
    ) -> Tuple[float, float]:
        """Converts Q-values/CVaR margins to calibrated spillback probability."""
        q_arr = self._extract_q_array(q_values)
        if q_arr is not None and q_arr.size >= 2:
            keep_idx = self.action_keep_stage
            change_idx = 1 if keep_idx == 0 else 0
            q_margin = float(q_arr[keep_idx] - q_arr[change_idx])
            if self.is_calibrated:
                raw = q_margin if cvar_margin is None else cvar_margin
                spread = max(quantile_spread or self.reference_spread, 0.25 * self.reference_spread, 1e-3)
                logit = float(np.clip(self.logit_scale * (raw / spread) + self.logit_bias, -20.0, 20.0))
            else:
                logit = float(np.clip(q_margin / self.calibration_temperature, -20.0, 20.0))
            return float(1.0 / (1.0 + np.exp(-logit))), q_margin

        if hasattr(q_values, "max"):
            act = q_values.max(1)[1].item()
            return (1.0, 5.0) if act == self.action_keep_stage else (0.0, -5.0)
        return 0.0, 0.0

    @staticmethod
    def _extract_q_array(q_values: Any) -> Optional[np.ndarray]:
        if hasattr(q_values, "_data") and isinstance(getattr(q_values, "_data", None), (list, tuple, np.ndarray)):
            return np.asarray(q_values._data, dtype=np.float32).reshape(-1)
        if isinstance(q_values, (np.ndarray, list, tuple)):
            return np.asarray(q_values, dtype=np.float32).reshape(-1)
        if isinstance(q_values, torch.Tensor):
            return q_values.detach().cpu().numpy().astype(np.float32).reshape(-1)
        return None

    def record_child_observation(self, margin: float, spread: float, spillback_flag: bool) -> None:
        self.child_observations.append((float(margin), max(float(spread), 1e-3), 1 if spillback_flag else 0))

    def record_td_loss(self, td_loss: float) -> None:
        if td_loss >= 0.0 and math.isfinite(td_loss):
            self.td_losses.append(float(td_loss))

    def finalize_child_calibration(self) -> Dict[str, Any]:
        """Fits quantile scale, logistic calibration, F2 threshold, and reliability on graduation."""
        self.child_learning_active = False
        self.is_frozen = True
        if len(self.child_observations) < 20:
            self.is_calibrated = True
            self.d3qn_reliability = 0.50
            return {"status": "fallback_insufficient_samples", "samples": len(self.child_observations)}

        arr = np.asarray(list(self.child_observations), dtype=np.float64)
        margins, spreads, labels = arr[:, 0], arr[:, 1], arr[:, 2]
        self.reference_spread = float(max(float(np.median(spreads)), 1e-3))
        x = margins / np.maximum(spreads, 0.25 * self.reference_spread)
        pos_count, neg_count = int(labels.sum()), int(len(labels) - labels.sum())

        if pos_count < 3 or neg_count < 3:
            self.logit_scale, self.logit_bias, self.d3qn_reliability = 1.0, 0.0, 0.40
            self.calibrated_threshold = min(self.spillback_floor, 0.72)
            self.is_calibrated = True
            return {"status": "low_positive_variance", "pos": pos_count, "neg": neg_count}

        self.logit_scale, self.logit_bias = self._fit_regularized_logistic(x, labels)
        probs = 1.0 / (1.0 + np.exp(-np.clip(self.logit_scale * x + self.logit_bias, -20.0, 20.0)))
        self.calibrated_threshold = self._select_f2_threshold(probs, labels)

        sep = max(0.0, float(probs[labels == 1].mean() - probs[labels == 0].mean()))
        mean_td = float(np.mean(self.td_losses)) if self.td_losses else 1.0
        self.d3qn_reliability = float(np.clip(0.50 + 0.50 * sep * math.exp(-min(mean_td, 20.0) / 10.0), 0.40, 0.98))
        self.is_calibrated = True
        return {
            "status": "calibrated",
            "logit_scale": self.logit_scale,
            "logit_bias": self.logit_bias,
            "threshold": self.calibrated_threshold,
            "d3qn_reliability": self.d3qn_reliability,
        }

    @staticmethod
    def _fit_regularized_logistic(x: np.ndarray, y: np.ndarray) -> Tuple[float, float]:
        w, b = 1.0, float(np.log((y.mean() + 1e-3) / (1.0 - y.mean() + 1e-3)))
        lr, l2, n = 0.15, 0.05, float(len(y))
        for _ in range(120):
            err = (1.0 / (1.0 + np.exp(-np.clip(w * x + b, -20.0, 20.0)))) - y
            w -= lr * float(np.dot(err, x) / n + l2 * (w - 1.0))
            b -= lr * float(err.mean() + l2 * b)
        return float(np.clip(w, 0.25, 10.0)), float(np.clip(b, -5.0, 5.0))

    def _select_f2_threshold(self, probs: np.ndarray, labels: np.ndarray) -> float:
        best_th, best_f2 = min(self.spillback_floor, 0.65), -1.0
        for th in np.linspace(0.45, self.spillback_floor, 15):
            preds = probs >= th
            tp = float(np.sum(preds & (labels == 1)))
            fp = float(np.sum(preds & (labels == 0)))
            fn = float(np.sum((~preds) & (labels == 1)))
            denom = 5.0 * tp + fp + 4.0 * fn
            f2 = (5.0 * tp / denom) if denom > 0.0 else 0.0
            if f2 > best_f2:
                best_f2, best_th = f2, float(th)
        return float(np.clip(best_th, 0.45, self.spillback_floor))

    def fuse_risks(
        self, kinematic_risk: float, neural_prob: float, pae_risk: Optional[float], pae_reliability: float = 0.85
    ) -> float:
        """Combines physical, PAE, and D3QN risks with non-compensatory Noisy-OR."""
        c_pae = float(np.clip(pae_reliability, 0.0, 1.0)) if pae_risk is not None else 0.0
        if self.child_learning_active and not self.is_calibrated:
            c_d3qn = 0.0
        elif self.is_calibrated:
            c_d3qn = self.d3qn_reliability
        else:
            c_d3qn = self.legacy_neural_weight if self.legacy_neural_weight is not None else 0.85

        surv = 1.0 - min(max(kinematic_risk, 0.0), self.CROMWELL_CAP)
        if pae_risk is not None:
            surv *= 1.0 - min(max(c_pae * pae_risk, 0.0), self.CROMWELL_CAP)
        surv *= 1.0 - min(max(c_d3qn * neural_prob, 0.0), self.CROMWELL_CAP)
        fused = float(np.clip(1.0 - surv, 0.0, self.CROMWELL_CAP))

        pae_crit = pae_risk is not None and c_pae >= 0.60 and pae_risk >= min(0.95, self.spillback_floor + 0.05)
        if kinematic_risk >= self.spillback_floor or pae_crit:
            fused = max(fused, min(self.CROMWELL_CAP, max(self.spillback_floor, kinematic_risk * self.CROMWELL_CAP)))
        return fused

    def effective_threshold(self, base_threshold: float) -> float:
        return (
            float(self.calibrated_threshold)
            if self.is_calibrated and self.calibrated_threshold
            else float(base_threshold)
        )

    def to_state_dict(self) -> Dict[str, Any]:
        return {
            "is_calibrated": self.is_calibrated,
            "is_frozen": self.is_frozen,
            "child_learning_active": self.child_learning_active,
            "logit_scale": self.logit_scale,
            "logit_bias": self.logit_bias,
            "reference_spread": self.reference_spread,
            "calibrated_threshold": self.calibrated_threshold,
            "d3qn_reliability": self.d3qn_reliability,
            "edge_feature_dim": self.edge_feature_dim,
            "edge_capacities": list(self.edge_capacities),
            "clearance_horizon_sec": self.clearance_horizon_sec,
            "step_dt_sec": self.physics.step_dt_sec,
        }

    def load_state_dict(self, data: Dict[str, Any]) -> None:
        if not isinstance(data, dict):
            return
        self.is_calibrated = bool(data.get("is_calibrated", self.is_calibrated))
        self.is_frozen = bool(data.get("is_frozen", self.is_frozen))
        self.child_learning_active = bool(data.get("child_learning_active", self.child_learning_active))
        self.logit_scale = float(data.get("logit_scale", self.logit_scale))
        self.logit_bias = float(data.get("logit_bias", self.logit_bias))
        self.reference_spread = max(1e-3, float(data.get("reference_spread", self.reference_spread)))
        self.calibrated_threshold = (
            float(data["calibrated_threshold"]) if data.get("calibrated_threshold") is not None else None
        )
        self.d3qn_reliability = float(data.get("d3qn_reliability", self.d3qn_reliability))
        self.physics.configure_topology(
            data.get("edge_feature_dim"), data.get("edge_capacities"), data.get("clearance_horizon_sec")
        )
        if data.get("step_dt_sec") is not None:
            self.physics.step_dt_sec = max(0.05, float(data["step_dt_sec"]))
