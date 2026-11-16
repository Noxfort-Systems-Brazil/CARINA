# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Resolves EVP preemption overrides and Guardian vetoes on authorized agent actions."""

import logging
from typing import Any, Optional, Tuple

import numpy as np
import torch

from engine.guardian_context_builder import GuardianContextBuilder


class ActionVetoResolver:
    """Applies EVP Green-Wave overrides and Guardian safety vetoes to stage-change actions."""

    def __init__(self, state_extractor: Any, action_supervisor: Any) -> None:
        self.state_extractor = state_extractor
        self.action_supervisor = action_supervisor

    @staticmethod
    def _apply_veto_override(
        agent: Any,
        state_tensor: torch.Tensor,
        precomputed_pae_latent: Optional[torch.Tensor],
    ) -> Tuple[int, torch.Tensor, torch.Tensor]:
        action_idx = torch.tensor([1], device=agent.device)
        with torch.no_grad():
            action_log_prob, _, _ = agent.evaluate(
                state_tensor, action_idx, precomputed_pae_latent=precomputed_pae_latent
            )
        return 1, action_idx, action_log_prob

    def resolve(
        self,
        tl_id: str,
        agent: Any,
        guardian: Optional[Any],
        current_stage_idx: int,
        sim_time: float,
        state_vector: np.ndarray,
        state_tensor: torch.Tensor,
        precomputed_pae_latent: Optional[torch.Tensor],
        action_int: int,
        action_idx: torch.Tensor,
        action_log_prob: torch.Tensor,
        is_auth: bool,
        reason: str,
        evp_override: Optional[str],
    ) -> Tuple[int, torch.Tensor, torch.Tensor, bool, str, bool]:
        guardian_vetoed = False
        if evp_override and is_auth and action_int == 0:
            v_label = evp_override.split(":", 1)[1] if ":" in evp_override else "Viatura"
            is_auth = False
            reason = f"PREEMPÇÃO EVP ATIVA ({v_label} no Corredor Verde)"
            guardian_vetoed = True
            logging.info(f"[AgentEvaluator] TL {tl_id} stage change VETOED by EVP Preemption: {v_label}")
            action_int, action_idx, action_log_prob = self._apply_veto_override(
                agent, state_tensor, precomputed_pae_latent
            )
        elif is_auth and action_int == 0 and guardian:
            context = GuardianContextBuilder.build_context(
                tl_id=tl_id,
                current_stage_idx=current_stage_idx,
                sim_time=sim_time,
                state_extractor=self.state_extractor,
                action_supervisor=self.action_supervisor,
            )
            guard_action, guard_reason = guardian.select_action(
                state_vector, context, precomputed_pae_latent=precomputed_pae_latent
            )
            if guard_action == guardian.ACTION_KEEP_STAGE:
                is_auth = False
                reason = f"VETADA PELO GUARDIÃO ({guard_reason})"
                guardian_vetoed = True
                logging.info(f"[AgentEvaluator] TL {tl_id} stage change VETOED by Guardian: {guard_reason}")
                action_int, action_idx, action_log_prob = self._apply_veto_override(
                    agent, state_tensor, precomputed_pae_latent
                )
            else:
                logging.info(f"[AgentEvaluator] TL {tl_id} stage change ALLOWED by Guardian: {guard_reason}")

        return action_int, action_idx, action_log_prob, is_auth, reason, guardian_vetoed
