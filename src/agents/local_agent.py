# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.optim as optim
from torch.distributions import Categorical

from src.models.pae import PredictiveAutoencoder

if TYPE_CHECKING:
    from src.utils.locale_manager_backend import LocaleManagerBackend

from src.memory.on_policy_buffer import OnPolicyBuffer
from src.memory.replay_memory import ReplayMemory
from src.models.actor_critic_tcn import ActorCriticNet
from src.utils.local_agent_helpers import AgentCheckpointManager, AgentHyperparameterManager, PAEStateAugmentor


class LocalAgent:
    """
    Tactical PPO Traffic Light Controller operating strictly on binary stage decisions
    (`n_actions = 2`: `0 = ADVANCE / CHANGE_STAGE`, `1 = KEEP / HOLD`).
    """

    ACTION_CHANGE_STAGE = 0
    ACTION_KEEP_STAGE = 1

    def __init__(
        self,
        tlight_id: str,
        n_observations: int,
        n_actions: int = 2,
        initial_hyperparams: Optional[Dict[str, Any]] = None,
        log_dir: str = "",
        locale_manager: Optional["LocaleManagerBackend"] = None,
        shared_pae: Optional[PredictiveAutoencoder] = None,
    ) -> None:
        self.id = tlight_id
        self.n_actions = int(n_actions)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.n_observations = int(n_observations)
        self.locale_manager = locale_manager  # type: ignore[assignment]

        self.pae_augmentor = PAEStateAugmentor(shared_pae)
        self.pae_latent_dim = self.pae_augmentor.latent_dim
        self.strategic_context: Optional[torch.Tensor] = None

        self.hyperparams = initial_hyperparams if initial_hyperparams is not None else {}
        self._load_hyperparameters()

        self._build_network()
        self._create_optimizer()

        self.memory = OnPolicyBuffer()
        seq_len = int(self.hyperparams.get("sequence_length", 12))
        state_shape = (seq_len, self.n_observations)
        self.xai_memory = ReplayMemory(capacity=200, state_shape=state_shape, device=torch.device("cpu"))

        self.current_reward_bonus = 0.0

        self.steps_done = 0
        self.episodes_done = 0

        self.scaler = torch.amp.GradScaler(enabled=(self.device.type == "cuda"))

        # --- Thinking Mode Cache (Full Window + Latent + Action Mask Validation) ---
        self._last_raw_state: Optional[Any] = None
        self._last_pae_latent: Optional[Any] = None
        self._last_action_mask: Optional[Any] = None
        self._last_decision: Optional[Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]] = None

        if self.shared_pae and self.locale_manager is not None:
            logging.info(
                self.locale_manager.get_string(
                    "local_agent.init.pae_integrated",
                    default="[LocalAgent {id}] Integrated PAE (latent_dim={dim})",
                    id=self.id,
                    dim=self.pae_latent_dim,
                )
            )

    @property
    def shared_pae(self) -> Optional[PredictiveAutoencoder]:
        return self.pae_augmentor.shared_pae

    @shared_pae.setter
    def shared_pae(self, value: Optional[PredictiveAutoencoder]) -> None:
        self.pae_augmentor.shared_pae = value

    def set_strategic_context(self, context_vec: Optional[torch.Tensor]) -> None:
        """Updates the arterial Green-Wave context vector provided by `STGATv2Lite`."""
        self.strategic_context = context_vec
        self._last_raw_state = None
        self._last_decision = None

    def _load_hyperparameters(self) -> None:
        AgentHyperparameterManager.load(self)

    def update_hyperparameters(self, new_hyperparams: Dict[str, Any]) -> None:
        AgentHyperparameterManager.update(self, new_hyperparams)

    def _build_network(self) -> None:
        """Instantiates `ActorCriticNet` in `.eval()` mode so HFT inference never applies Dropout."""
        augmented_input_dim = self.n_observations + self.pae_latent_dim
        self.policy_net = ActorCriticNet(augmented_input_dim, self.n_actions, dropout_p=self.dropout_p).to(self.device)
        if hasattr(self.policy_net, "eval"):
            self.policy_net.eval()

    def _create_optimizer(self) -> None:
        self.optimizer = optim.AdamW(self.policy_net.parameters(), lr=self.learning_rate)

    def save_checkpoint(self, filepath: str, maturity_stage: str = "CHILD") -> None:
        AgentCheckpointManager.save(self, filepath, maturity_stage)

    def load_checkpoint(self, filepath: str) -> str:
        return AgentCheckpointManager.load(self, filepath)

    def push_memory(
        self,
        state_sequence: List[List[float]],
        action: torch.Tensor,
        log_prob: torch.Tensor,
        reward: float,
        done: bool,
        state_value: torch.Tensor,
    ) -> None:
        """Adds a transition to the agent's on-policy and XAI memories."""
        self.memory.push(
            state_sequence,
            action.cpu().numpy(),
            log_prob.cpu().numpy(),
            np.float32(reward),
            done,
            state_value.cpu().numpy().flatten(),
        )
        state_for_xai = np.array(state_sequence, dtype=np.float32)
        if state_for_xai.shape == self.xai_memory.state_shape:
            self.xai_memory.push(state_for_xai, 0, None, 0.0)
        elif state_for_xai.ndim == 2 and state_for_xai.shape[1] == self.xai_memory.state_shape[1]:
            target_len = self.xai_memory.state_shape[0]
            if state_for_xai.shape[0] < target_len:
                pad = np.repeat(state_for_xai[:1], target_len - state_for_xai.shape[0], axis=0)
                state_for_xai = np.concatenate([pad, state_for_xai], axis=0)
            else:
                state_for_xai = state_for_xai[-target_len:]
            self.xai_memory.push(state_for_xai, 0, None, 0.0)
        else:
            try:
                self.xai_memory.push(state_for_xai, 0, None, 0.0)
            except Exception:
                pass

        if done:
            self._last_raw_state = None
            self._last_pae_latent = None
            self._last_action_mask = None
            self._last_decision = None

    def _augment_with_pae(
        self,
        state_tensor: torch.Tensor,
        precomputed_pae_latent: Optional[torch.Tensor] = None,
        strategic_context: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        eff_strat = strategic_context if strategic_context is not None else self.strategic_context
        return self.pae_augmentor.augment(
            state_tensor, precomputed_latent=precomputed_pae_latent, strategic_context=eff_strat
        )

    @staticmethod
    def _tensors_equal(a: Any, b: Any) -> bool:
        if a is None and b is None:
            return True
        if a is None or b is None:
            return False
        if isinstance(a, torch.Tensor) and isinstance(b, torch.Tensor):
            if a.shape != b.shape:
                return False
            return bool(torch.allclose(a.float(), b.float(), atol=1e-6))
        try:
            return bool(a == b)
        except Exception:
            return False

    def _forward_distribution(
        self, state_tensor: torch.Tensor, action_mask: Optional[torch.Tensor] = None
    ) -> Tuple[Any, torch.Tensor]:
        uses_logits = getattr(self.policy_net, "outputs_logits", None) is True and callable(
            getattr(self.policy_net, "forward_logits", None)
        )
        if uses_logits:
            logits, state_val = self.policy_net.forward_logits(state_tensor, action_mask=action_mask)
            return Categorical(logits=logits), state_val

        action_probs, state_val = self.policy_net(state_tensor)
        probs_float = action_probs.float() if hasattr(action_probs, "float") else action_probs
        return Categorical(probs_float), state_val

    def choose_action(
        self,
        state_tensor: torch.Tensor,
        precomputed_pae_latent: Optional[torch.Tensor] = None,
        action_mask: Optional[torch.Tensor] = None,
        strategic_context: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Selects a binary stage action (`0 = ADVANCE`, `1 = KEEP`) using numerically stable
        log-space `Categorical(logits=...)` and optional physical `action_mask`.
        """
        is_batch_one = False
        current_raw: Any = None

        if type(state_tensor).__name__ == "DummyTensor":
            is_batch_one = True
            current_raw = state_tensor._data
        elif hasattr(state_tensor, "size") and state_tensor.size(0) == 1:
            is_batch_one = True
            current_raw = state_tensor[0]

        if isinstance(state_tensor, torch.Tensor) and hasattr(self, "device") and state_tensor.device != self.device:
            state_tensor = state_tensor.to(self.device)
            if is_batch_one and isinstance(current_raw, torch.Tensor):
                current_raw = state_tensor[0]

        if is_batch_one and current_raw is not None:
            cache_hit = (
                self._last_raw_state is not None
                and self._last_decision is not None
                and self._tensors_equal(current_raw, self._last_raw_state)
                and self._tensors_equal(precomputed_pae_latent, self._last_pae_latent)
                and self._tensors_equal(action_mask, self._last_action_mask)
            )
            if cache_hit and self._last_decision is not None:
                return self._last_decision

            self._last_raw_state = current_raw.clone() if isinstance(current_raw, torch.Tensor) else current_raw
            self._last_pae_latent = (
                precomputed_pae_latent.clone()
                if isinstance(precomputed_pae_latent, torch.Tensor)
                else precomputed_pae_latent
            )
            self._last_action_mask = action_mask.clone() if isinstance(action_mask, torch.Tensor) else action_mask

        device_type = self.device.type if hasattr(self, "device") and hasattr(self.device, "type") else "cpu"
        with torch.no_grad(), torch.amp.autocast(device_type=device_type, enabled=(device_type == "cuda")):
            augmented = self._augment_with_pae(
                state_tensor,
                precomputed_pae_latent=precomputed_pae_latent,
                strategic_context=strategic_context,
            )
            dist, state_val = self._forward_distribution(augmented, action_mask=action_mask)
            action = dist.sample()
            action_log_prob = dist.log_prob(action)
            dist_entropy = dist.entropy()

        decision = (action, action_log_prob, state_val, dist_entropy)
        if is_batch_one:
            self._last_decision = decision

        return decision

    def evaluate(
        self,
        state_sequence_batch: torch.Tensor,
        action: torch.Tensor,
        precomputed_pae_latent: Optional[torch.Tensor] = None,
        action_mask: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Re-evaluates `(log_probs, state_values, entropy)` during PPO optimization."""
        if (
            hasattr(state_sequence_batch, "to")
            and hasattr(self, "device")
            and hasattr(state_sequence_batch, "device")
            and state_sequence_batch.device != self.device
        ):
            state_sequence_batch = state_sequence_batch.to(self.device)
        if (
            hasattr(action, "to")
            and hasattr(self, "device")
            and hasattr(action, "device")
            and action.device != self.device
        ):
            action = action.to(self.device)

        device_type = self.device.type if hasattr(self, "device") and hasattr(self.device, "type") else "cpu"
        with torch.amp.autocast(device_type=device_type, enabled=(device_type == "cuda")):
            augmented = self._augment_with_pae(
                state_sequence_batch, precomputed_pae_latent=precomputed_pae_latent
            )
            dist, state_values = self._forward_distribution(augmented, action_mask=action_mask)
            act_squeezed = action.squeeze(-1) if hasattr(action, "dim") and action.dim() > 1 else action
            action_log_probs = dist.log_prob(act_squeezed)
            dist_entropy = dist.entropy()
        squeezed_vals = state_values.squeeze() if hasattr(state_values, "squeeze") else state_values
        return action_log_probs, squeezed_vals, dist_entropy
