# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Legacy architecture migration, input-channel adaptation, and XAI replay restoration."""

import copy
from typing import Any, Dict, Optional

import torch
import torch.nn as nn

try:
    from src.memory.replay_memory import ReplayMemory
except ImportError:
    from memory.replay_memory import ReplayMemory


_FIRST_CONV_CANDIDATES = (
    "tcn.network.0.conv1.weight",
    "tcn.network.0.conv1.weight_v",
    "tcn.network.0.net.0.weight",
    "tcn.network.0.net.0.weight_v",
)

_ADAPT_WEIGHT_KEYS = (
    "tcn.network.0.conv1.weight",
    "tcn.network.0.net.0.weight",
    "tcn.network.0.conv1.weight_v",
    "tcn.network.0.net.0.weight_v",
    "tcn.network.0.downsample.weight",
)


class CheckpointMigrator:
    """Migrates legacy checkpoint tensors and XAI buffers onto modernized architectures."""

    @staticmethod
    def find_first_conv_key(state_dict: Dict[str, Any]) -> Optional[str]:
        for candidate in _FIRST_CONV_CANDIDATES:
            if candidate in state_dict:
                return candidate
        return None

    @staticmethod
    def load_into_policy_net(policy_net: Any, state_dict: Dict[str, Any], target_dict: Dict[str, Any]) -> None:
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
    def _reconstruct_weight_norm(migrated: Dict[str, Any], target_state_dict: Dict[str, Any]) -> None:
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

    @staticmethod
    def _split_post_tcn_trunk(migrated: Dict[str, Any], target_state_dict: Dict[str, Any]) -> None:
        post_keys = [k for k in list(migrated.keys()) if k.startswith("post_tcn_layer.")]
        for pk in post_keys:
            suffix = pk[len("post_tcn_layer.") :]
            val = migrated.pop(pk)
            for trunk_prefix in ("actor_trunk", "critic_trunk"):
                target_key = f"{trunk_prefix}.{suffix}"
                if target_key in target_state_dict and target_key not in migrated:
                    migrated[target_key] = val.clone() if hasattr(val, "clone") else val

    @staticmethod
    def _adapt_action_heads(migrated: Dict[str, Any], target_state_dict: Dict[str, Any]) -> None:
        for w_name, b_name in (
            ("actor_head.0.weight", "actor_head.0.bias"),
            ("actor_head.weight", "actor_head.bias"),
        ):
            if w_name not in migrated or w_name not in target_state_dict:
                continue
            w_old = migrated[w_name]
            w_tgt = target_state_dict[w_name]
            if not (
                hasattr(w_old, "shape")
                and hasattr(w_tgt, "shape")
                and len(w_old.shape) == 2
                and len(w_tgt.shape) == 2
                and w_old.shape[0] != w_tgt.shape[0]
                and w_old.shape[1] == w_tgt.shape[1]
            ):
                continue

            is_legacy_ternary = w_old.shape[0] == 3 and w_tgt.shape[0] == 2
            w_new = w_tgt.clone()
            if is_legacy_ternary:
                w_new[0] = w_old[0]  # 0 = ADVANCE / CHANGE_STAGE
                w_new[1] = 0.5 * (w_old[1] + w_old[2])  # 1 = KEEP / HOLD
            else:
                min_a = min(w_old.shape[0], w_tgt.shape[0])
                w_new[:min_a] = w_old[:min_a]
            migrated[w_name] = w_new

            if b_name in migrated and b_name in target_state_dict:
                b_old = migrated[b_name]
                b_new = target_state_dict[b_name].clone()
                if is_legacy_ternary:
                    b_new[0] = b_old[0]
                    if isinstance(b_old, torch.Tensor) and isinstance(getattr(nn, "Linear", None), type):
                        b_new[1] = torch.logsumexp(b_old[1:3], dim=0)
                    else:
                        b_new[1] = 0.5 * (b_old[1] + b_old[2])
                else:
                    min_a = min(w_old.shape[0], w_tgt.shape[0])
                    b_new[:min_a] = b_old[:min_a]
                migrated[b_name] = b_new

    @staticmethod
    def migrate_legacy_architecture_keys(
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
        CheckpointMigrator._reconstruct_weight_norm(migrated, target_state_dict)
        CheckpointMigrator._split_post_tcn_trunk(migrated, target_state_dict)
        CheckpointMigrator._adapt_action_heads(migrated, target_state_dict)
        return migrated

    @staticmethod
    def adapt_input_channel_weights(
        agent: Any,
        raw_state_dict: Dict[str, Any],
        in_channels: int,
        checkpoint_n_obs: Optional[int],
        cur_pae_latent: int,
    ) -> None:
        """Rebuilds `agent.policy_net` for new channel width and copies overlapping obs/PAE slices."""
        agent._build_network()
        agent._create_optimizer()

        old_n_obs = in_channels if checkpoint_n_obs is None else min(checkpoint_n_obs, in_channels)
        old_latent_dim = max(0, in_channels - old_n_obs)
        min_obs = min(old_n_obs, agent.n_observations)
        min_latent = min(old_latent_dim, cur_pae_latent)

        new_state_dict = agent.policy_net.state_dict()
        adapted_dict = CheckpointMigrator.migrate_legacy_architecture_keys(
            copy.deepcopy(raw_state_dict), new_state_dict
        )

        for key in _ADAPT_WEIGHT_KEYS:
            if key in adapted_dict and key in new_state_dict:
                w_old = adapted_dict[key]
                w_new = new_state_dict[key].clone()
                w_new[:, :min_obs, :] = w_old[:, :min_obs, :]
                if min_latent > 0:
                    w_new[:, agent.n_observations : agent.n_observations + min_latent, :] = w_old[
                        :, old_n_obs : old_n_obs + min_latent, :
                    ]
                adapted_dict[key] = w_new

        CheckpointMigrator.load_into_policy_net(agent.policy_net, adapted_dict, new_state_dict)

    @staticmethod
    def restore_xai_memory(agent: Any, loaded_xai_memory: Any) -> None:
        """Restores XAI replay buffer onto CPU, supporting compact serialized dicts and legacy oversized buffers."""
        if not loaded_xai_memory:
            return
        if isinstance(loaded_xai_memory, dict) and "_compact_xai_states" in loaded_xai_memory:
            states_tensor = loaded_xai_memory["_compact_xai_states"].cpu()
            cap = max(200, int(loaded_xai_memory.get("capacity", 200)))
            state_shape = tuple(loaded_xai_memory.get("state_shape") or tuple(states_tensor.shape[1:]))
            new_mem = ReplayMemory(capacity=cap, state_shape=state_shape, device=torch.device("cpu"))
            n_items = min(int(states_tensor.shape[0]), cap)
            if n_items > 0:
                new_mem.states[:n_items] = states_tensor[:n_items]
                new_mem.size = n_items
                new_mem.ptr = n_items % cap
            agent.xai_memory = new_mem
            return
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

            new_mem = ReplayMemory(capacity=200, state_shape=xai_state_shape, device=torch.device("cpu"))
            num_to_copy = min(loaded_xai_memory.size, 200)
            for i in range(num_to_copy):
                idx = (loaded_xai_memory.ptr - num_to_copy + i) % loaded_xai_memory.capacity
                st = loaded_xai_memory.states[idx].cpu()
                act = loaded_xai_memory.actions[idx].cpu()
                rew = loaded_xai_memory.rewards[idx].cpu()
                new_mem.push(st, act, None, rew)
            agent.xai_memory = new_mem
            return

        agent.xai_memory = loaded_xai_memory
        agent.xai_memory.device = torch.device("cpu")
        for attr in ("states", "actions", "next_states", "rewards", "non_final_mask", "priorities"):
            setattr(agent.xai_memory, attr, getattr(agent.xai_memory, attr).cpu())
        if not hasattr(agent.xai_memory, "action_dtype"):
            agent.xai_memory.action_dtype = getattr(agent.xai_memory.actions, "dtype", torch.long)
        if not hasattr(agent.xai_memory, "action_shape"):
            agent.xai_memory.action_shape = (
                tuple(agent.xai_memory.actions.shape[1:])
                if hasattr(agent.xai_memory, "actions") and agent.xai_memory.actions.ndim > 1
                else (1,)
            )
