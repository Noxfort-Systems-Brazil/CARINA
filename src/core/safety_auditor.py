# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.guardian_agent import GuardianAgent
    from engine.environment import SumoEnvironment

logger = logging.getLogger(__name__)


class SafetyAuditor:
    """
    Applies Neuro-Symbolic vetoes via the Guardian Agent.
    """

    def __init__(self, guardian_agent: "GuardianAgent"):
        self.guardian = guardian_agent
        self.last_veto_reasons = {}

    def audit(
        self,
        suggested_action: int,
        tl_id: str,
        augmented_state: list,
        environment: "SumoEnvironment",
        latest_veto_map: dict = None,
    ) -> tuple:
        """
        Audits a 'CHANGE PHASE' request using the Guardian logic.
        Returns: (final_action, was_vetoed)
        """
        if suggested_action != 0:
            self.last_veto_reasons[tl_id] = "Nenhum (Decisão Aprovada)"
            return suggested_action, False

        extractor = environment.state_extractor

        sim_time = 0.0
        current_stage_idx = 0
        if environment.conn:
            try:
                sim_time = environment.conn.simulation.getTime()
                current_stage_idx = environment.conn.trafficlight.getPhase(tl_id)
            except Exception as exc:
                logger.error(
                    "[SafetyAuditor] Falha ao consultar fase/tempo para %s: %s. Veto conservador (fail-safe) aplicado.",
                    tl_id,
                    exc,
                 exc_info=True)
                self.last_veto_reasons[tl_id] = f"Veto Fail-Safe (Erro de Telemetria: {type(exc).__name__})"
                return 1, True

        current_stage_duration = 0.0
        if environment.action_supervisor:
            current_stage_duration = sim_time - environment.action_supervisor._last_stage_change_time.get(tl_id, 0.0)

        # 0. Emergency Priority Interception (EVP - Emergency Vehicle Preemption)
        try:
            from evp.evp_bridge import EVPBridge

            bridge = EVPBridge()
            evp_action, is_evp, _ = bridge.intercept_safety_audit(
                tl_id=tl_id,
                current_stage=current_stage_idx,
                stage_duration=current_stage_duration,
                suggested_action=suggested_action,
            )
            if is_evp and evp_action is not None:
                if evp_action == 1:
                    self.last_veto_reasons[tl_id] = "Preempção de Veículo de Emergência (EVP - Corredor Verde Ativo)"
                return evp_action, (evp_action == 1)
        except Exception as exc:
            logger.error("[SafetyAuditor] Falha na interceptação EVP para %s: %s", tl_id, exc, exc_info=True)

        stage_codes = extractor.tl_stage_codes.get(tl_id, {})
        state_string = stage_codes.get(current_stage_idx, "G")

        # Improve context with more accurate information
        total_stages = len(stage_codes)
        prev_stage_idx = (current_stage_idx - 1) % total_stages if total_stages > 0 else 0
        prev_state_string = stage_codes.get(prev_stage_idx, "").upper()

        stage_durations = getattr(extractor, "tl_stage_durations", {}).get(tl_id, {})
        default_duration = stage_durations.get(current_stage_idx, 0.0)
        from utils.safety_rules import SafetyRules

        all_red_time = SafetyRules.get_all_red()
        if default_duration > 0:
            is_clearance_red = ("Y" in prev_state_string) and (default_duration <= all_red_time)
        else:
            is_clearance_red = "Y" in prev_state_string

        context = {
            "tl_id": tl_id,
            "current_stage_duration": current_stage_duration,
            "current_stage_state": state_string.upper(),
            "next_stage_has_flow": True,
            "is_clearance_red": is_clearance_red,
            "max_green_time": SafetyRules.get_max_green(),
        }

        # 1. Immediate Symbolic Audit
        if self.guardian:
            symbolic_action, reason = self.guardian.symbolic_audit(context)
            if symbolic_action == 0:  # Vetoed by symbolic rules
                self.last_veto_reasons[tl_id] = reason
                return 1, True

        # 2. Maximum Green Ceiling (Anti-Starvation / Force-off)
        max_green_time = float(context.get("max_green_time", SafetyRules.get_max_green()))
        if "G" in state_string.upper() and current_stage_duration >= max_green_time:
            self.last_veto_reasons[tl_id] = "Nenhum (Teto Máximo de Verde Excedido - Forçamento)"
            return suggested_action, False

        # 3. Zero-Latency Neural Spillback Audit (from Background Veto Map)
        if latest_veto_map and tl_id in latest_veto_map:
            veto_val = latest_veto_map[tl_id]
            risk_score = veto_val.get("risk", veto_val) if isinstance(veto_val, dict) else veto_val
            is_exploratory = veto_val.get("is_exploratory", False) if isinstance(veto_val, dict) else False
            # If risk is extremely high, veto the change
            if risk_score > 0.8:
                if is_exploratory:
                    self.last_veto_reasons[tl_id] = "Intervenção exploratória de spillback (Treino/Exploração)"
                else:
                    self.last_veto_reasons[tl_id] = "Veto Crítico de Spillback (Redes Neurais D3QN)"
                return 1, True

        self.last_veto_reasons[tl_id] = "Nenhum (Decisão Aprovada)"
        return suggested_action, False
