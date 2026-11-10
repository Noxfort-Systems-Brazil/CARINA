# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import copy
import logging
import os
from typing import TYPE_CHECKING, Any, Dict, Optional

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from memory.replay_memory import ReplayMemory

if TYPE_CHECKING:
    from agents.local_agent import LocalAgent


class PAEStateAugmentor:
    """
    Handles Universal PAE latent projection, optional ST-GATv2 strategic context fusion,
    and temporal sequence state augmentation without breaking agent channel dimensions.
    """

    def __init__(self, shared_pae: Optional[Any] = None) -> None:
        self.shared_pae = shared_pae
        self.latent_dim = shared_pae.latent_dim if shared_pae else 0

    @staticmethod
    def _align_context_to_dim(vec: torch.Tensor, target_dim: int) -> torch.Tensor:
        """Projects/pads/pools a `[batch, gat_dim]` strategic vector onto `[batch, target_dim]`."""
        cur_dim = vec.size(-1)
        if cur_dim == target_dim:
            return vec
        if cur_dim < target_dim:
            return F.pad(vec, (0, target_dim - cur_dim))
        # Adaptive average pool across feature groups when gat_dim > target_dim
        return F.adaptive_avg_pool1d(vec.unsqueeze(1), target_dim).squeeze(1)

    def augment(
        self,
        state_tensor: torch.Tensor,
        precomputed_latent: Optional[torch.Tensor] = None,
        strategic_context: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        if self.shared_pae is None and precomputed_latent is None:
            return state_tensor

        with torch.no_grad():
            if precomputed_latent is not None:
                latent = precomputed_latent
                if hasattr(latent, "dim") and latent.dim() == 1:
                    latent = latent.unsqueeze(0)
            elif self.shared_pae is not None:
                latent = self.shared_pae.encode(state_tensor)  # [batch, latent_dim]
            else:
                return state_tensor

            if hasattr(latent, "to"):
                if (
                    hasattr(state_tensor, "device")
                    and hasattr(latent, "device")
                    and latent.device != state_tensor.device
                ):
                    latent = latent.to(state_tensor.device)
                if (
                    hasattr(state_tensor, "dtype")
                    and hasattr(latent, "dtype")
                    and latent.dtype != state_tensor.dtype
                ):
                    latent = latent.to(dtype=state_tensor.dtype)

            # Residual arterial Green-Wave strategic fusion (ST-GATv2 -> latent context)
            if (
                strategic_context is not None
                and isinstance(getattr(nn, "Linear", None), type)
                and isinstance(latent, torch.Tensor)
                and latent.size(-1) > 0
            ):
                strat = strategic_context
                if hasattr(strat, "dim") and strat.dim() == 1:
                    strat = strat.unsqueeze(0)
                if strat.device != latent.device or strat.dtype != latent.dtype:
                    strat = strat.to(device=latent.device, dtype=latent.dtype)
                if strat.size(0) == 1 and latent.size(0) > 1:
                    strat = strat.expand(latent.size(0), -1)
                strat_aligned = self._align_context_to_dim(strat, latent.size(-1))
                latent = latent + 0.25 * torch.tanh(strat_aligned)

            latent_expanded = latent.unsqueeze(1).expand(-1, state_tensor.size(1), -1)  # [batch, seq_len, latent_dim]
            return torch.cat([state_tensor, latent_expanded], dim=-1)


class AgentHyperparameterManager:
    """Manages hyperparameters and applies them to networks and optimizers."""

    @staticmethod
    def load(agent: "LocalAgent") -> None:
        agent.gamma = float(agent.hyperparams.get("gamma", 0.99))
        agent.gae_lambda = float(agent.hyperparams.get("gae_lambda", 0.95))
        agent.learning_rate = float(agent.hyperparams.get("learning_rate", 0.0001))
        agent.eps_clip = float(agent.hyperparams.get("eps_clip", 0.2))
        agent.k_epochs = int(agent.hyperparams.get("k_epochs", 4))
        agent.target_kl = float(agent.hyperparams.get("target_kl", 0.02))
        agent.grad_clip_norm = float(agent.hyperparams.get("grad_clip_norm", 0.5))
        agent.dropout_p = float(agent.hyperparams.get("dropout_p", 0.1))
        agent.critic_loss_coef = float(agent.hyperparams.get("critic_loss_coef", 0.5))

    @staticmethod
    def update(agent: "LocalAgent", new_hyperparams: Dict[str, Any]) -> None:
        agent.hyperparams = new_hyperparams
        AgentHyperparameterManager.load(agent)
        if agent.optimizer:
            agent.optimizer.param_groups[0]["lr"] = agent.learning_rate
        if agent.policy_net and hasattr(agent.policy_net, "modules"):
            for module in agent.policy_net.modules():
                try:
                    if isinstance(module, nn.Dropout):
                        module.p = agent.dropout_p
                except TypeError:
                    pass


class AgentCheckpointManager:
    """Handles serialization, channel adaptation, and legacy `3 -> 2` binary action migration."""

    @staticmethod
    def save(agent: "LocalAgent", filepath: str, maturity_stage: str) -> None:
        checkpoint = {
            "episodes_done": agent.episodes_done,
            "steps_done": agent.steps_done,
            "policy_net_state_dict": agent.policy_net.state_dict(),
            "optimizer_state_dict": agent.optimizer.state_dict(),
            "hyperparameters": agent.hyperparams,
            "xai_memory": agent.xai_memory,
            "n_observations": agent.n_observations,
            "n_actions": getattr(agent, "n_actions", 2),
            "maturity_stage": maturity_stage,
        }
        torch.save(checkpoint, filepath)
        try:
            from database.database_manager import DatabaseManager
            from utils.paths import get_base_output_dir

            db = getattr(agent, "db_manager", None) or DatabaseManager.get_instance(agent.locale_manager)
            base_dir = os.path.join(get_base_output_dir(), "results")
            db.sync_file_to_vault(filepath, base_dir)
        except Exception:
            pass

    @staticmethod
    def _migrate_legacy_architecture_keys(
        state_dict: Dict[str, Any], target_state_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Migrates legacy checkpoint keys to the modernized `ActorCriticNet` layout:
        1. Reconstructs standard `.weight` from legacy `weight_v` + `weight_g` when target uses `.weight`.
        2. Copies legacy `post_tcn_layer.*` weights into decoupled `actor_trunk.*` and `critic_trunk.*`.
        3. Adapts legacy 3-action (`[ADVANCE, HOLD_1, HOLD_2]`) actor heads to binary 2-action (`[ADVANCE, KEEP]`).
        """
        if not isinstance(state_dict, dict) or not isinstance(target_state_dict, dict) or not target_state_dict:
            return state_dict

        migrated = dict(state_dict)

        # 1. Convert legacy weight_norm (weight_v / weight_g) -> standard conv weight if target uses .weight
        wv_keys = [k for k in list(migrated.keys()) if k.endswith(".weight_v")]
        for wv_key in wv_keys:
            base_prefix = wv_key[: -len(".weight_v")]
            w_key = f"{base_prefix}.weight"
            wg_key = f"{base_prefix}.weight_g"
            if w_key in target_state_dict and wv_key not in target_state_dict:
                wv = migrated.pop(wv_key)
                wg = migrated.pop(wg_key, None)
                if wg is not None and isinstance(wv, torch.Tensor) and isinstance(wg, torch.Tensor):
                    dims = tuple(range(1, wv.dim()))
                    norm = torch.linalg.vector_norm(wv, dim=dims, keepdim=True).clamp(min=1e-12)
                    migrated[w_key] = wv * (wg / norm)
                else:
                    migrated[w_key] = wv

        # 2. Migrate legacy shared post_tcn_layer -> decoupled actor_trunk & critic_trunk
        post_keys = [k for k in list(migrated.keys()) if k.startswith("post_tcn_layer.")]
        for pk in post_keys:
            suffix = pk[len("post_tcn_layer.") :]
            val = migrated.pop(pk)
            actor_k = f"actor_trunk.{suffix}"
            critic_k = f"critic_trunk.{suffix}"
            if actor_k in target_state_dict and actor_k not in migrated:
                migrated[actor_k] = val.clone() if hasattr(val, "clone") else val
            if critic_k in target_state_dict and critic_k not in migrated:
                migrated[critic_k] = val.clone() if hasattr(val, "clone") else val

        # 3. Binary action adaptation (legacy n_actions=3 -> n_actions=2)
        for w_name, b_name in [
            ("actor_head.0.weight", "actor_head.0.bias"),
            ("actor_head.weight", "actor_head.bias"),
        ]:
            if w_name in migrated and w_name in target_state_dict:
                w_old = migrated[w_name]
                w_tgt = target_state_dict[w_name]
                if (
                    hasattr(w_old, "shape")
                    and hasattr(w_tgt, "shape")
                    and len(w_old.shape) == 2
                    and len(w_tgt.shape) == 2
                    and w_old.shape[0] != w_tgt.shape[0]
                    and w_old.shape[1] == w_tgt.shape[1]
                ):
                    if w_old.shape[0] == 3 and w_tgt.shape[0] == 2:
                        w_new = w_tgt.clone()
                        w_new[0] = w_old[0]  # 0 = ADVANCE / CHANGE_STAGE
                        w_new[1] = 0.5 * (w_old[1] + w_old[2])  # 1 = KEEP / HOLD
                        migrated[w_name] = w_new
                        if b_name in migrated and b_name in target_state_dict:
                            b_old = migrated[b_name]
                            b_new = target_state_dict[b_name].clone()
                            b_new[0] = b_old[0]
                            if isinstance(b_old, torch.Tensor) and isinstance(getattr(nn, "Linear", None), type):
                                b_new[1] = torch.logsumexp(b_old[1:3], dim=0)
                            else:
                                b_new[1] = 0.5 * (b_old[1] + b_old[2])
                            migrated[b_name] = b_new
                    else:
                        min_a = min(w_old.shape[0], w_tgt.shape[0])
                        w_new = w_tgt.clone()
                        w_new[:min_a] = w_old[:min_a]
                        migrated[w_name] = w_new
                        if b_name in migrated and b_name in target_state_dict:
                            b_old = migrated[b_name]
                            b_new = target_state_dict[b_name].clone()
                            b_new[:min_a] = b_old[:min_a]
                            migrated[b_name] = b_new

        return migrated

    @staticmethod
    def _find_first_conv_key(state_dict: Dict[str, Any]) -> Optional[str]:
        for candidate in (
            "tcn.network.0.conv1.weight",
            "tcn.network.0.conv1.weight_v",
            "tcn.network.0.net.0.weight",
            "tcn.network.0.net.0.weight_v",
        ):
            if candidate in state_dict:
                return candidate
        return None

    @staticmethod
    def _load_into_policy_net(policy_net: Any, state_dict: Dict[str, Any], target_dict: Dict[str, Any]) -> None:
        """Loads `state_dict`, filling missing newly-introduced keys from `target_dict` when needed."""
        if isinstance(target_dict, dict) and target_dict:
            merged = dict(target_dict)
            for k, v in state_dict.items():
                if k in merged:
                    merged[k] = v
            policy_net.load_state_dict(merged)
        else:
            policy_net.load_state_dict(state_dict)

    @staticmethod
    def load(agent: "LocalAgent", filepath: str) -> str:
        lm = agent.locale_manager
        saved_maturity = "CHILD"

        if not os.path.exists(filepath):
            try:
                from database.database_manager import DatabaseManager
                from utils.paths import get_base_output_dir

                db = getattr(agent, "db_manager", None) or DatabaseManager.get_instance(lm)
                base_dir = os.path.join(get_base_output_dir(), "results")
                rel_path = os.path.relpath(filepath, base_dir)
                db.restore_file_from_vault(rel_path, filepath)
            except Exception as e:
                logging.warning(f"[AgentCheckpointManager] Vault restoration check error for {filepath}: {e}", exc_info=True)

        try:
            try:
                checkpoint = torch.load(filepath, map_location=agent.device, weights_only=True)
            except Exception:
                checkpoint = torch.load(filepath, map_location=agent.device, weights_only=False)  # nosec B614

            if agent.n_observations != checkpoint.get("n_observations"):
                logging.warning(
                    lm.get_string(
                        "local_agent.load.obs_mismatch_warning",
                        agent_id=agent.id,
                        chk_obs=checkpoint.get("n_observations"),
                        cur_obs=agent.n_observations,
                    )
                )

            saved_maturity = checkpoint.get("maturity_stage", "CHILD")

            dim_adapted = False
            raw_state_dict = checkpoint.get("policy_net_state_dict")
            target_state_dict = agent.policy_net.state_dict() if hasattr(agent.policy_net, "state_dict") else {}
            state_dict = (
                AgentCheckpointManager._migrate_legacy_architecture_keys(raw_state_dict, target_state_dict)
                if isinstance(raw_state_dict, dict)
                else raw_state_dict
            )
            action_adapted = (
                isinstance(raw_state_dict, dict)
                and isinstance(state_dict, dict)
                and raw_state_dict.keys() != state_dict.keys()
            ) or (
                checkpoint.get("n_actions") is not None
                and checkpoint.get("n_actions") != getattr(agent, "n_actions", 2)
            )

            conv_key = AgentCheckpointManager._find_first_conv_key(state_dict) if isinstance(state_dict, dict) else None
            if isinstance(state_dict, dict) and conv_key is not None:
                try:
                    in_channels = state_dict[conv_key].shape[1]
                    cur_pae_latent = agent.pae_augmentor.latent_dim if getattr(agent, "pae_augmentor", None) else 0
                    agent.pae_latent_dim = cur_pae_latent
                    expected_channels = agent.n_observations + cur_pae_latent

                    if in_channels != expected_channels:
                        logging.info(
                            f"[LocalAgentHelpers] Adapting checkpoint weights for agent {agent.id}: "
                            f"checkpoint has {in_channels} channels, current model expects {expected_channels} "
                            f"(n_obs={agent.n_observations}, pae_latent={cur_pae_latent})."
                        )
                        agent._build_network()
                        agent._create_optimizer()

                        old_n_obs = checkpoint.get("n_observations", in_channels)
                        if old_n_obs > in_channels:
                            old_n_obs = in_channels
                        old_latent_dim = max(0, in_channels - old_n_obs)
                        min_obs = min(old_n_obs, agent.n_observations)
                        min_latent = min(old_latent_dim, cur_pae_latent)

                        new_state_dict = agent.policy_net.state_dict()
                        adapted_dict = AgentCheckpointManager._migrate_legacy_architecture_keys(
                            copy.deepcopy(raw_state_dict), new_state_dict
                        )

                        for key in (
                            "tcn.network.0.conv1.weight",
                            "tcn.network.0.net.0.weight",
                            "tcn.network.0.conv1.weight_v",
                            "tcn.network.0.net.0.weight_v",
                        ):
                            if key in adapted_dict and key in new_state_dict:
                                w_old = adapted_dict[key]
                                w_new = new_state_dict[key].clone()
                                w_new[:, :min_obs, :] = w_old[:, :min_obs, :]
                                if min_latent > 0:
                                    w_new[:, agent.n_observations : agent.n_observations + min_latent, :] = (
                                        w_old[:, old_n_obs : old_n_obs + min_latent, :]
                                    )
                                adapted_dict[key] = w_new

                        downsample_key = "tcn.network.0.downsample.weight"
                        if downsample_key in adapted_dict and downsample_key in new_state_dict:
                            w_old = adapted_dict[downsample_key]
                            w_new = new_state_dict[downsample_key].clone()
                            w_new[:, :min_obs, :] = w_old[:, :min_obs, :]
                            if min_latent > 0:
                                w_new[:, agent.n_observations : agent.n_observations + min_latent, :] = (
                                    w_old[:, old_n_obs : old_n_obs + min_latent, :]
                                )
                            adapted_dict[downsample_key] = w_new

                        AgentCheckpointManager._load_into_policy_net(agent.policy_net, adapted_dict, new_state_dict)
                        dim_adapted = True
                except Exception as e:
                    logging.warning(
                        f"[LocalAgentHelpers] Failed to adapt weights for agent {agent.id}: {e}. "
                        "Rebuilding model with expected channels."
                    , exc_info=True)
                    agent._build_network()
                    agent._create_optimizer()
                    dim_adapted = True

            if "hyperparameters" in checkpoint:
                agent.update_hyperparameters(checkpoint["hyperparameters"])

            if not dim_adapted and state_dict is not None:
                try:
                    AgentCheckpointManager._load_into_policy_net(
                        agent.policy_net, state_dict, target_state_dict if isinstance(target_state_dict, dict) else {}
                    )
                    if "optimizer_state_dict" in checkpoint and not action_adapted:
                        try:
                            agent.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
                        except Exception:
                            agent._create_optimizer()
                except Exception as e:
                    logging.warning(f"[LocalAgentHelpers] Error loading state dict: {e}. Reinitializing policy net.", exc_info=True)
                    agent._build_network()
                    agent._create_optimizer()

            agent.episodes_done = checkpoint.get("episodes_done", 0)
            agent.steps_done = checkpoint.get("steps_done", 0)

            loaded_xai_memory = checkpoint.get("xai_memory")
            if loaded_xai_memory:
                if getattr(loaded_xai_memory, "capacity", 0) > 200:
                    raw_xai_shape = getattr(getattr(agent, "xai_memory", None), "state_shape", None)
                    if (
                        isinstance(raw_xai_shape, tuple)
                        and len(raw_xai_shape) > 0
                        and all(isinstance(d, int) for d in raw_xai_shape)
                    ):
                        xai_state_shape = raw_xai_shape
                    elif getattr(loaded_xai_memory, "size", 0) > 0 and hasattr(loaded_xai_memory, "states"):
                        sample_st = loaded_xai_memory.states[0]
                        xai_state_shape = (
                            tuple(sample_st.shape)
                            if hasattr(sample_st, "shape") and len(sample_st.shape) > 0
                            else (int(agent.n_observations),)
                        )
                    else:
                        xai_state_shape = (int(agent.n_observations),)

                    new_mem = ReplayMemory(
                        capacity=200, state_shape=xai_state_shape, device=torch.device("cpu")
                    )
                    num_to_copy = min(loaded_xai_memory.size, 200)
                    for i in range(num_to_copy):
                        idx = (loaded_xai_memory.ptr - num_to_copy + i) % loaded_xai_memory.capacity
                        st = loaded_xai_memory.states[idx].cpu()
                        act = loaded_xai_memory.actions[idx].cpu()
                        rew = loaded_xai_memory.rewards[idx].cpu()
                        new_mem.push(st, act, None, rew)
                    agent.xai_memory = new_mem
                else:
                    agent.xai_memory = loaded_xai_memory
                    agent.xai_memory.device = torch.device("cpu")
                    agent.xai_memory.states = agent.xai_memory.states.cpu()
                    agent.xai_memory.actions = agent.xai_memory.actions.cpu()
                    agent.xai_memory.next_states = agent.xai_memory.next_states.cpu()
                    agent.xai_memory.rewards = agent.xai_memory.rewards.cpu()
                    agent.xai_memory.non_final_mask = agent.xai_memory.non_final_mask.cpu()
                    agent.xai_memory.priorities = agent.xai_memory.priorities.cpu()
                    if not hasattr(agent.xai_memory, "action_dtype"):
                        agent.xai_memory.action_dtype = getattr(agent.xai_memory.actions, "dtype", torch.long)
                    if not hasattr(agent.xai_memory, "action_shape"):
                        agent.xai_memory.action_shape = (
                            tuple(agent.xai_memory.actions.shape[1:])
                            if hasattr(agent.xai_memory, "actions") and agent.xai_memory.actions.ndim > 1
                            else (1,)
                        )

            # Set evaluation mode (train(False) == eval(), disabling Dropout during HFT inference)
            agent.policy_net.train(False)
            agent._last_raw_state = None
            agent._last_decision = None
            logging.info(
                lm.get_string(
                    "local_agent.load.success", agent_id=agent.id, path=filepath, count=len(agent.xai_memory)
                )
            )

        except FileNotFoundError:
            logging.warning(lm.get_string("local_agent.load.not_found_warning", agent_id=agent.id, path=filepath))
        except Exception as e:
            logging.error(lm.get_string("local_agent.load.error", agent_id=agent.id, error=e), exc_info=True)

        return saved_maturity
