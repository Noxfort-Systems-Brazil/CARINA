# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import random
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import torch
import torch.optim as optim

if TYPE_CHECKING:
    from src.utils.locale_manager_backend import LocaleManagerBackend

from src.agents.guardian_neural_predictor import GuardianNeuralPredictor
from src.memory.replay_memory import ReplayMemory
from src.models.d3qn_tcn import D3QN_TCN
from src.models.pae import PredictiveAutoencoder
from src.safety.guardian_symbolic_auditor import GuardianSymbolicAuditor
from src.utils.safety_rules import SafetyRules


class GuardianAgent:
    """
    The Neuro-Symbolic Guardian Agent (HFT Predictive).
    Combines D3QN_TCN with dynamic safety rules (Symbolic) loaded from settings.ini.
    Acts as a safety shield, vetoing actions violating engineering constraints.
    Delegates neural prediction and sequence buffers to GuardianNeuralPredictor (SRP).
    """

    ACTION_KEEP_STAGE = 0
    ACTION_CHANGE_STAGE = 1
    TEMPORAL_SEQ_LEN = 8

    def __init__(
        self,
        aiconfig: Any,
        traffic_rules_config: Any,
        locale_manager: "LocaleManagerBackend",
        shared_pae: Optional[PredictiveAutoencoder] = None,
        n_observations: int = 2,
        edge_feature_dim: Optional[int] = None,
        edge_capacities: Optional[List[float]] = None,
    ) -> None:
        self.locale_manager = locale_manager
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._load_hyperparameters(aiconfig)

        self.shared_pae = shared_pae
        self.pae_latent_dim = shared_pae.latent_dim if shared_pae else 0

        # --- Configurable Safety Rules (Symbolic Layer) ---
        self.green_time = SafetyRules.get_green()
        self.yellow_time = SafetyRules.get_yellow()
        self.all_red_time = SafetyRules.get_all_red()
        self.red_time = SafetyRules.get_red()
        self.symbolic_auditor = GuardianSymbolicAuditor(
            green_time=self.green_time,
            yellow_time=self.yellow_time,
            all_red_time=self.all_red_time,
            red_time=self.red_time,
            locale_manager=self.locale_manager,
        )

        # --- Neural Layer (D3QN + TCN + PAE Fusion) ---
        self.n_observations = n_observations
        self.policy_net = D3QN_TCN(
            n_observations=self.n_observations, n_actions=2, pae_latent_dim=self.pae_latent_dim
        ).to(self.device)
        self.policy_net.eval()
        self.target_net = D3QN_TCN(
            n_observations=self.n_observations, n_actions=2, pae_latent_dim=self.pae_latent_dim
        ).to(self.device)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()

        self.optimizer = optim.AdamW(self.policy_net.parameters(), lr=self.learning_rate)
        state_shape = (self.TEMPORAL_SEQ_LEN, self.n_observations)
        self.memory = ReplayMemory(
            self.memory_size,
            state_shape=state_shape,
            device=self.device,
            storage_device=torch.device("cpu"),
        )

        self.steps_done = 0
        self.is_training: bool = False
        self.is_frozen: bool = False
        self._last_is_exploratory: Dict[str, bool] = {}
        self.scaler = torch.amp.GradScaler(enabled=(self.device.type == "cuda"))

        # Dedicated Neural Predictor (SRP / Clean Architecture)
        self.neural_predictor = GuardianNeuralPredictor(
            policy_net=self.policy_net,
            target_net=self.target_net,
            device=self.device,
            shared_pae=self.shared_pae,
            temporal_seq_len=self.TEMPORAL_SEQ_LEN,
            action_keep_stage=self.ACTION_KEEP_STAGE,
            calibration_temperature=self.calibration_temperature,
            neural_weight=self.neural_risk_weight,
            clearance_horizon_sec=self.yellow_time + self.all_red_time,
            edge_feature_dim=edge_feature_dim,
            edge_capacities=edge_capacities,
        )

    @property
    def calibrator(self) -> Any:
        return self.neural_predictor.calibrator

    @property
    def state_deques(self) -> Dict:
        return self.neural_predictor.state_deques

    @state_deques.setter
    def state_deques(self, val: Dict) -> None:
        self.neural_predictor.state_deques = val

    def _load_hyperparameters(self, cfg: Any) -> None:
        self.batch_size = cfg.getint("batch_size", 128)
        self.gamma = cfg.getfloat("gamma", 0.90)
        self.epsilon_start = cfg.getfloat("epsilon_start", 1.0)
        self.epsilon_end = cfg.getfloat("epsilon_end", 0.05)
        self.epsilon_decay = cfg.getint("epsilon_decay", 30000)
        self.learning_rate = cfg.getfloat("learning_rate", 0.00025)
        self.memory_size = cfg.getint("memory_size", 50000)
        raw_thresh = float(cfg.getfloat("spillback_risk_threshold", 0.65)) if hasattr(cfg, "getfloat") else 0.65
        self.spillback_risk_threshold = min(max(raw_thresh, 0.1), 0.99)
        raw_temp = float(cfg.getfloat("calibration_temperature", 1.0)) if hasattr(cfg, "getfloat") else 1.0
        self.calibration_temperature = max(raw_temp, 1e-3)
        raw_weight = float(cfg.getfloat("neural_risk_weight", 0.85)) if hasattr(cfg, "getfloat") else 0.85
        self.neural_risk_weight = min(max(raw_weight, 0.0), 1.0)

    def _get_temporal_sequence(self, state: List[float], tl_id: str) -> torch.Tensor:
        return self.neural_predictor.get_temporal_sequence(state, tl_id)

    def _get_pae_latent(self, seq_tensor: torch.Tensor) -> torch.Tensor:
        return self.neural_predictor.get_pae_latent(seq_tensor)

    def configure_topology(
        self, edge_feature_dim: Optional[int] = None, edge_capacities: Optional[List[float]] = None
    ) -> None:
        """Sets true incoming edge slice length and vehicle capacities from network topology."""
        self.calibrator.configure_topology(
            edge_feature_dim=edge_feature_dim,
            edge_capacities=edge_capacities,
            clearance_horizon_sec=self.yellow_time + self.all_red_time,
        )

    def freeze_for_deployment(self) -> None:
        """
        Locks neural weights into deterministic inference mode upon leaving `Maturity.CHILD`
        and releases training-only `target_net`, `optimizer`, and PER `memory` buffers.
        """
        self.is_frozen = True
        self.calibrator.is_frozen = True
        self.calibrator.child_learning_active = False
        self.is_training = False
        if hasattr(self.policy_net, "eval"):
            self.policy_net.eval()
        if hasattr(self.policy_net, "parameters"):
            try:
                for param in self.policy_net.parameters():
                    if isinstance(param, torch.Tensor):
                        param.requires_grad_(False)
            except Exception:
                pass

        self.target_net = None
        if hasattr(self, "neural_predictor") and self.neural_predictor is not None:
            self.neural_predictor.target_net = None
        self.optimizer = None
        if getattr(self, "memory", None) is not None and callable(getattr(self.memory, "release", None)):
            self.memory.release()

    def finalize_child_calibration(self) -> Dict[str, Any]:
        """Fits post-`CHILD` quantile calibration and locks weights for `TEEN`/`ADULT` deployment."""
        if self.calibrator.is_calibrated and self.is_frozen and len(self.calibrator.child_observations) == 0:
            return {"status": "already_calibrated"}
        stats = self.calibrator.finalize_child_calibration()
        self.spillback_risk_threshold = self.calibrator.effective_threshold(self.spillback_risk_threshold)
        self.freeze_for_deployment()
        return stats

    def train(self, mode: bool = True) -> "GuardianAgent":
        if self.is_frozen and mode:
            self.is_training = False
            self.policy_net.eval()
            return self
        self.is_training = bool(mode)
        self.policy_net.train(self.is_training)
        return self

    def eval(self) -> "GuardianAgent":
        return self.train(False)

    def is_exploratory_decision(self, tl_id: str) -> bool:
        return False

    def select_action(
        self, state: List[float], context: Dict[str, Any], precomputed_pae_latent: Optional[torch.Tensor] = None
    ) -> Tuple[int, str]:
        tl_id = context.get("tl_id", "unknown")

        sym_action, sym_reason = self.symbolic_audit(context)
        if sym_action == self.ACTION_KEEP_STAGE:
            return sym_action, sym_reason

        current_stage_duration = float(context.get("current_stage_duration", 0.0))
        current_stage_state = str(context.get("current_stage_state", "G")).upper()
        max_green_time = float(context.get("max_green_time", SafetyRules.get_max_green()))
        if "G" in current_stage_state and current_stage_duration >= max_green_time:
            return self.ACTION_CHANGE_STAGE, self.locale_manager.get_string(
                "guardian_agent.reasons.max_green_exceeded",
                default="Maximum green time ceiling reached (force-off)",
            )

        latent = precomputed_pae_latent if precomputed_pae_latent is not None else context.get("precomputed_pae_latent")
        risk_level = self.evaluate_spillback_risk(state, tl_id, precomputed_pae_latent=latent)
        default_thresh = self.calibrator.effective_threshold(self.spillback_risk_threshold)
        threshold = float(context.get("spillback_risk_threshold", default_thresh))
        if risk_level >= threshold:
            return self.ACTION_KEEP_STAGE, self.locale_manager.get_string(
                "guardian_agent.reasons.spillback", default="High spillback risk detected (Neural)"
            )

        return self.ACTION_CHANGE_STAGE, self.locale_manager.get_string(
            "guardian_agent.reasons.neuro_passed", default="Neuro-Symbolic audit passed"
        )

    def symbolic_audit(self, context: Dict[str, Any]) -> Tuple[int, str]:
        return self.symbolic_auditor.audit(context)

    def evaluate_spillback_risk(
        self,
        state: List[float],
        tl_id: str,
        *args: Any,
        precomputed_pae_latent: Optional[torch.Tensor] = None,
        **kwargs: Any,
    ) -> float:
        return self.neural_predictor.evaluate_spillback_risk(
            state, tl_id, precomputed_pae_latent=precomputed_pae_latent
        )

    def evaluate_spillback_breakdown(
        self, state: List[float], tl_id: str, precomputed_pae_latent: Optional[torch.Tensor] = None
    ) -> Dict[str, float]:
        return self.neural_predictor.evaluate_spillback_breakdown(
            state, tl_id, precomputed_pae_latent=precomputed_pae_latent
        )

    def forward_policy(self, states_batch: torch.Tensor) -> torch.Tensor:
        return self.neural_predictor.forward_policy(states_batch)

    def forward_target(self, states_batch: torch.Tensor) -> torch.Tensor:
        return self.neural_predictor.forward_target(states_batch)

    def forward_policy_quantiles(self, states_batch: torch.Tensor) -> torch.Tensor:
        return self.neural_predictor.forward_policy_quantiles(states_batch)

    def forward_target_quantiles(self, states_batch: torch.Tensor) -> torch.Tensor:
        return self.neural_predictor.forward_target_quantiles(states_batch)
