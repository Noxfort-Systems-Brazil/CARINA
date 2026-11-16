# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Physical safety action masking for tactical agents (yellow/red clearance & green bounds)."""

import sys
from typing import Any, Optional

import torch

try:
    from utils.safety_rules import SafetyRules
except ImportError:
    from src.utils.safety_rules import SafetyRules

try:
    from models.actor_critic_tcn import ActorCriticNet as _RelActorCriticNet
except ImportError:
    _RelActorCriticNet = None

try:
    from src.models.actor_critic_tcn import ActorCriticNet as _SrcActorCriticNet
except ImportError:
    _SrcActorCriticNet = None


def _is_actor_critic_net(policy_net: Any) -> bool:
    """Handles both `models.*` and `src.models.*` module aliases consistently."""
    if policy_net is None:
        return False
    candidates = [cls for cls in (_RelActorCriticNet, _SrcActorCriticNet) if isinstance(cls, type)]
    for mod_name in ("models.actor_critic_tcn", "src.models.actor_critic_tcn"):
        mod = sys.modules.get(mod_name)
        cls = getattr(mod, "ActorCriticNet", None) if mod is not None else None
        if isinstance(cls, type) and cls not in candidates:
            candidates.append(cls)
    return bool(candidates) and isinstance(policy_net, tuple(candidates))


class PhysicalActionMasker:
    """
    Computes binary action masks `[1, 2]` -> `[allow_advance (0), allow_keep (1)]`
    enforcing yellow/all-red clearance, minimum green, and maximum green constraints.
    """

    def __init__(self, state_extractor: Any, action_supervisor: Any) -> None:
        self.state_extractor = state_extractor
        self.action_supervisor = action_supervisor
        self._mask_cache: dict[tuple[str, bool, bool], torch.Tensor] = {}

    def _get_last_change_time(self, tl_id: str) -> Optional[float]:
        getter = getattr(self.action_supervisor, "get_last_stage_change_time", None)
        if callable(getter):
            val = getter(tl_id, default=0.0)
            if isinstance(val, (int, float)):
                return float(val)
        last_change_map = getattr(self.action_supervisor, "_last_stage_change_time", None)
        if isinstance(last_change_map, dict):
            return float(last_change_map.get(tl_id, 0.0))
        return None

    def compute_mask(
        self,
        tl_id: str,
        agent: Any,
        current_stage_idx: int,
        sim_time: float,
    ) -> Optional[torch.Tensor]:
        if not _is_actor_critic_net(getattr(agent, "policy_net", None)):
            return None

        stage_codes_all = getattr(self.state_extractor, "tl_stage_codes", None)
        if not isinstance(stage_codes_all, dict):
            return None

        last_change = self._get_last_change_time(tl_id)
        if last_change is None:
            return None

        stage_codes = stage_codes_all.get(tl_id)
        if not isinstance(stage_codes, dict) or not stage_codes:
            return None

        state_str = str(stage_codes.get(current_stage_idx, "G")).upper()
        elapsed = float(sim_time) - last_change

        allow_advance = True
        allow_keep = True

        if "Y" in state_str and "G" not in state_str:
            allow_advance = False
        elif "G" not in state_str and "Y" not in state_str:
            allow_advance = False
        else:
            min_green = SafetyRules.get_green()
            max_green = SafetyRules.get_max_green()
            if elapsed < min_green:
                allow_advance = False
            elif max_green > min_green and elapsed >= max_green:
                allow_keep = False

        if not allow_advance and not allow_keep:
            allow_keep = True

        device = getattr(agent, "device", torch.device("cpu"))
        if type(torch).__name__ != "DummyTorch":
            cache_key = (str(device), allow_advance, allow_keep)
            cached = self._mask_cache.get(cache_key)
            if cached is not None:
                return cached
            mask = torch.tensor([[allow_advance, allow_keep]], dtype=torch.bool, device=device)
            self._mask_cache[cache_key] = mask
            return mask
        return torch.tensor([[allow_advance, allow_keep]], dtype=torch.bool, device=device)
