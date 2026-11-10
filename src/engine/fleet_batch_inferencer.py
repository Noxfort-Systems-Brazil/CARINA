# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Vectorized Fleet Batch Inferencer for CARINA HFT Tactical Controllers.

Groups `LocalAgent` instances sharing the same neural topology signature
`(augmented_input_dim, n_actions, hidden_size, device)` and executes a single
vectorized forward pass via `torch.func.stack_module_state` + `torch.vmap`,
eliminating $O(N)$ sequential Python/CUDA kernel launch overhead across citywide
intersections while preserving exact numerical equivalence with single-agent `.eval()`.
"""

import copy
import logging
from typing import Any, Dict, List, Optional, Tuple

import torch
import torch.nn as nn
from torch.distributions import Categorical

from src.models.actor_critic_tcn import ActorCriticNet


class FleetBatchInferencer:
    """
    Executes batched tactical policy inference across homogeneous groups of `LocalAgent`s
    with automatic Thinking-Mode cache reuse and safe fallback to sequential execution.
    """

    def __init__(self) -> None:
        self._has_functorch = bool(
            isinstance(getattr(nn, "Linear", None), type)
            and hasattr(torch, "func")
            and getattr(torch, "func", None) is not None
            and hasattr(torch.func, "stack_module_state")
            and hasattr(torch.func, "vmap")
            and hasattr(torch.func, "functional_call")
        )
        self._meta_templates: Dict[Tuple[int, int, int, int, str], ActorCriticNet] = {}

    @staticmethod
    def _is_batchable_agent(agent: Any) -> bool:
        net = getattr(agent, "policy_net", None)
        return (
            isinstance(net, ActorCriticNet)
            and not getattr(net, "training", False)
            and callable(getattr(agent, "_augment_with_pae", None))
        )

    def infer_fleet(
        self,
        agents: Dict[str, Any],
        precomputed_states: Optional[Dict[str, Any]] = None,
        precomputed_latents: Optional[Dict[str, torch.Tensor]] = None,
        action_masks: Optional[Dict[str, Optional[torch.Tensor]]] = None,
        precomputed_tensors: Optional[Dict[str, torch.Tensor]] = None,
    ) -> Dict[str, Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]]:
        """
        Computes `(action, log_prob, state_val, entropy)` for batchable `LocalAgent`s.
        Agents omitted from the returned dict (e.g. `MagicMock`s in unit tests) fall back
        transparently to individual `agent.choose_action(...)`.
        """
        results: Dict[str, Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]] = {}
        state_map = precomputed_states if precomputed_states is not None else (precomputed_tensors or {})
        latents_map = precomputed_latents or {}
        if len(state_map) < 2:
            return results

        # Group batchable agents that miss their Thinking-Mode cache by architecture signature
        groups: Dict[Tuple[int, int, int, int, str], List[Tuple[str, Any, torch.Tensor, Optional[torch.Tensor]]]] = {}

        for tl_id, agent in agents.items():
            if tl_id not in state_map or not self._is_batchable_agent(agent):
                continue

            entry = state_map[tl_id]
            state_tensor = entry[1] if isinstance(entry, tuple) and len(entry) >= 2 else entry
            pae_latent = latents_map.get(tl_id)
            act_mask = action_masks.get(tl_id) if action_masks else None

            if isinstance(state_tensor, torch.Tensor) and state_tensor.device != agent.device:
                state_tensor = state_tensor.to(agent.device)

            # Check Thinking Mode cache first (O(1) reuse for static intersections)
            if hasattr(state_tensor, "size") and state_tensor.size(0) == 1:
                curr_raw = state_tensor[0]
                if (
                    getattr(agent, "_last_raw_state", None) is not None
                    and getattr(agent, "_last_decision", None) is not None
                    and agent._tensors_equal(curr_raw, agent._last_raw_state)
                    and agent._tensors_equal(pae_latent, getattr(agent, "_last_pae_latent", None))
                    and agent._tensors_equal(act_mask, getattr(agent, "_last_action_mask", None))
                ):
                    results[tl_id] = agent._last_decision
                    continue

            if not self._has_functorch:
                results[tl_id] = agent.choose_action(
                    state_tensor,
                    precomputed_pae_latent=pae_latent,
                    action_mask=act_mask,
                )
                continue

            net: ActorCriticNet = agent.policy_net
            sig = (
                net.n_observations,
                net.n_actions,
                net.hidden_size,
                int(state_tensor.size(1)),
                str(agent.device),
            )
            groups.setdefault(sig, []).append((tl_id, agent, state_tensor, act_mask))

        for sig, items in groups.items():
            if len(items) < 2:
                # Single agent in this signature group: standard choose_action is optimal
                tl_id, agent, state_t, act_mask = items[0]
                results[tl_id] = agent.choose_action(
                    state_t,
                    precomputed_pae_latent=latents_map.get(tl_id),
                    action_mask=act_mask,
                )
                continue

            try:
                models = [it[1].policy_net for it in items]
                device = items[0][1].device
                device_type = device.type if hasattr(device, "type") else "cpu"
                n_actions = sig[1]

                with torch.no_grad(), torch.amp.autocast(device_type=device_type, enabled=(device_type == "cuda")):
                    aug_tensors: List[torch.Tensor] = []
                    mask_tensors: List[torch.Tensor] = []
                    has_any_mask = False

                    for tl_id, agent, state_t, act_mask in items:
                        aug = agent._augment_with_pae(
                            state_t, precomputed_pae_latent=latents_map.get(tl_id)
                        )
                        aug_tensors.append(aug)  # [1, seq_len, aug_dim]
                        if act_mask is not None:
                            has_any_mask = True
                            m = act_mask.to(device=device, dtype=torch.bool).view(1, n_actions)
                            mask_tensors.append(m)
                        else:
                            mask_tensors.append(torch.ones((1, n_actions), device=device, dtype=torch.bool))

                    stacked_inputs = torch.stack(aug_tensors, dim=0)  # [G, 1, seq_len, aug_dim]
                    params, buffers = torch.func.stack_module_state(models)
                    base_model = self._meta_templates.get(sig)
                    if base_model is None:
                        base_model = copy.deepcopy(models[0]).to("meta")
                        base_model.eval()
                        self._meta_templates[sig] = base_model

                    def _single_forward(p: Any, b: Any, x_i: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
                        return torch.func.functional_call(base_model, (p, b), (x_i,), {"return_logits": True})

                    raw_logits, raw_vals = torch.func.vmap(_single_forward)(
                        params, buffers, stacked_inputs
                    )  # [G, 1, n_actions], [G, 1, 1]

                    logits_2d = raw_logits.squeeze(1).float()  # [G, n_actions]
                    if has_any_mask:
                        stacked_masks = torch.cat(mask_tensors, dim=0)  # [G, n_actions]
                        logits_2d = ActorCriticNet.apply_action_mask(logits_2d, stacked_masks)

                    dist = Categorical(logits=logits_2d)
                    actions_b = dist.sample()  # [G]
                    log_probs_b = dist.log_prob(actions_b)  # [G]
                    entropies_b = dist.entropy()  # [G]

                vals_fp32 = raw_vals.float() if hasattr(raw_vals, "float") else raw_vals
                for idx, (tl_id, agent, state_t, act_mask) in enumerate(items):
                    dec = (
                        actions_b[idx : idx + 1],
                        log_probs_b[idx : idx + 1],
                        vals_fp32[idx],
                        entropies_b[idx : idx + 1],
                    )
                    if state_t.size(0) == 1:
                        agent._last_raw_state = state_t[0].clone()
                        lat = latents_map.get(tl_id)
                        agent._last_pae_latent = lat.clone() if isinstance(lat, torch.Tensor) else lat
                        agent._last_action_mask = act_mask.clone() if isinstance(act_mask, torch.Tensor) else act_mask
                        agent._last_decision = dec
                    results[tl_id] = dec

            except Exception as e_batch:
                logging.debug(f"[FleetBatchInferencer] Fallback to sequential execution for group {sig}: {e_batch}")
                for tl_id, agent, state_t, act_mask in items:
                    results[tl_id] = agent.choose_action(
                        state_t,
                        precomputed_pae_latent=latents_map.get(tl_id),
                        action_mask=act_mask,
                    )

        return results
