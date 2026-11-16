# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Physical Kinematic & PAE World-Model Spillback Estimator for GuardianAgent.

Handles strict incoming-edge state slicing (excluding phase encodings and
HistoricalAggregator tail blocks), road-capacity queue normalization, clearance
horizon projection (`H = yellow + all_red`), and counterfactual PAE evaluation
with dynamic MSE + heteroscedastic uncertainty weighting.
"""

import math
from typing import Any, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn


class GuardianPhysicsEstimator:
    """Computes physical kinematic saturation and counterfactual PAE spillback forecasts."""

    DEFAULT_CAPACITY_VEH = 20.0

    def __init__(
        self,
        edge_feature_dim: Optional[int] = None,
        edge_capacities: Optional[List[float]] = None,
        clearance_horizon_sec: float = 6.0,
        step_dt_sec: float = 0.25,
    ) -> None:
        self.edge_feature_dim = int(edge_feature_dim) if edge_feature_dim and edge_feature_dim >= 3 else None
        self.edge_capacities = [max(1.0, float(c)) for c in edge_capacities] if edge_capacities else []
        self.clearance_horizon_sec = max(float(clearance_horizon_sec), 0.5)
        self.step_dt_sec = max(float(step_dt_sec), 0.05)
        self.latest_pae_mse: Optional[float] = None

    def configure_topology(
        self,
        edge_feature_dim: Optional[int] = None,
        edge_capacities: Optional[List[float]] = None,
        clearance_horizon_sec: Optional[float] = None,
    ) -> None:
        """Updates incoming edge slice boundaries, vehicle capacities, and clearance time."""
        if edge_feature_dim is not None and edge_feature_dim >= 3:
            self.edge_feature_dim = int(edge_feature_dim)
        if edge_capacities is not None:
            self.edge_capacities = [max(1.0, float(c)) for c in edge_capacities]
        if clearance_horizon_sec is not None and clearance_horizon_sec > 0.0:
            self.clearance_horizon_sec = float(clearance_horizon_sec)

    def extract_saturation(
        self,
        vec: np.ndarray,
        edge_feature_dim: Optional[int] = None,
        edge_capacities: Optional[List[float]] = None,
    ) -> float:
        """Extracts peak physical saturation `[0.0, 1.0]` strictly from incoming-edge triplets."""
        if vec.size == 0:
            return 0.0
        clipped = np.clip(vec.astype(np.float32), 0.0, 1.0)
        dim_limit = edge_feature_dim if edge_feature_dim is not None else self.edge_feature_dim
        if dim_limit is not None and dim_limit >= 3:
            usable = min(clipped.size, (int(dim_limit) // 3) * 3)
        elif clipped.size >= 3:
            usable = (clipped.size // 3) * 3
        else:
            return float(np.max(clipped))
        if usable < 3:
            return float(np.max(clipped))

        edge_slice = clipped[:usable]
        occupancies = edge_slice[0::3]
        raw_queues = edge_slice[2::3]
        caps = edge_capacities if edge_capacities is not None else self.edge_capacities
        if caps:
            cap_arr = np.asarray(caps[: occupancies.size], dtype=np.float32)
            if cap_arr.size < occupancies.size:
                pad = np.full(occupancies.size - cap_arr.size, self.DEFAULT_CAPACITY_VEH, dtype=np.float32)
                cap_arr = np.concatenate([cap_arr, pad])
            cap_arr = np.maximum(cap_arr, 1.0)
            scaled_queues = np.clip((raw_queues * self.DEFAULT_CAPACITY_VEH) / cap_arr, 0.0, 1.0)
        else:
            scaled_queues = raw_queues
        return float(np.clip(np.max(np.maximum(occupancies, scaled_queues)), 0.0, 1.0))

    def compute_kinematic_risk(self, history: List[Any], fallback_state: List[float]) -> float:
        """Projects saturation over clearance horizon `H = yellow + all_red`."""
        frames = history if history else [fallback_state]
        if not frames:
            return 0.0
        curr_vec = np.asarray(frames[-1], dtype=np.float32).reshape(-1)
        curr_sat = self.extract_saturation(curr_vec)
        if len(frames) < 2:
            return curr_sat

        first_vec = np.asarray(frames[0], dtype=np.float32).reshape(-1)
        first_sat = self.extract_saturation(first_vec) if first_vec.size == curr_vec.size else curr_sat
        window_sec = max(self.step_dt_sec, float(len(frames) - 1) * self.step_dt_sec)
        growth_per_sec = max(0.0, curr_sat - first_sat) / window_sec
        projected = curr_sat + growth_per_sec * self.clearance_horizon_sec
        return float(np.clip(max(curr_sat, projected), 0.0, 1.0))

    def compute_pae_reliability(self, pae_mse: Optional[float], log_var_mean: Optional[float]) -> float:
        """Computes dynamic reliability `[0.05, 1.0]` from PAE error and epistemic log-variance."""
        eff_mse = self.latest_pae_mse if pae_mse is None else pae_mse
        if eff_mse is None and log_var_mean is None:
            return 0.85
        mse_factor = math.exp(-max(0.0, float(eff_mse)) / 0.10) if eff_mse is not None else 1.0
        unc_factor = math.exp(-max(0.0, float(log_var_mean)) / 2.0) if log_var_mean is not None else 1.0
        return float(np.clip(mse_factor * unc_factor, 0.05, 1.0))

    def compute_pae_forecast_risk(
        self, shared_pae: Any, pae_latent: torch.Tensor, device: Any, valid_dim: Optional[int] = None
    ) -> Tuple[Optional[float], float]:
        """Evaluates counterfactual PAE risk (`0=ADVANCE` vs `1=KEEP`) and dynamic reliability."""
        if shared_pae is None or not hasattr(shared_pae, "decode"):
            return None, 0.0
        try:
            dev_type = device.type if hasattr(device, "type") else "cpu"
            is_real_torch = isinstance(getattr(nn, "Linear", None), type)
            with torch.no_grad(), torch.amp.autocast(device_type=dev_type, enabled=(dev_type == "cuda")):
                if is_real_torch and hasattr(shared_pae, "decode_with_uncertainty"):
                    mean_adv, logv_adv = shared_pae.decode_with_uncertainty(pae_latent, action=0)
                    mean_keep, _ = shared_pae.decode_with_uncertainty(pae_latent, action=1)
                    if isinstance(mean_adv, torch.Tensor) and isinstance(logv_adv, torch.Tensor):
                        std_adv = torch.exp(0.5 * logv_adv)
                        ucb_adv = (mean_adv.float() + 0.5 * std_adv.float()).detach().cpu().numpy().reshape(-1)
                        keep_np = mean_keep.float().detach().cpu().numpy().reshape(-1)
                        if valid_dim and valid_dim > 0:
                            ucb_adv, keep_np = ucb_adv[:valid_dim], keep_np[:valid_dim]
                        sat_adv = self.extract_saturation(ucb_adv)
                        sat_keep = self.extract_saturation(keep_np)
                        delta = max(0.0, sat_adv - sat_keep)
                        logv_mean = float(logv_adv.float().mean().item())
                        return float(np.clip(sat_adv + delta, 0.0, 1.0)), self.compute_pae_reliability(None, logv_mean)
                pred_next = shared_pae.decode(pae_latent)
                if isinstance(pred_next, torch.Tensor):
                    pred_np = pred_next.detach().cpu().float().numpy().reshape(-1)
                    if valid_dim and valid_dim > 0:
                        pred_np = pred_np[:valid_dim]
                    return self.extract_saturation(pred_np), self.compute_pae_reliability(None, None)
        except Exception:
            return None, 0.0
        return None, 0.0
