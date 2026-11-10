# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Safe EVP Integration Bridge with CARINA_CORE Core.
Connects EVPService with SafetyAuditor, GuardianAgent, and GoGatewayClient,
ensuring Neuro-Symbolic Override and Loss Masking without amnesia or destabilization.
"""

import logging
from typing import Any, Dict, Optional, Tuple

from src.evp.evp_service import EVPService

logger = logging.getLogger(__name__)


class EVPBridge:
    """
    Integration bridge between the EVP module and existing CARINA_CORE subsystems.
    """

    def __init__(self, evp_service: Optional[EVPService] = None):
        self.evp_service = evp_service or EVPService.get_instance()
        self._bind_gateway_dispatcher()

    def _bind_gateway_dispatcher(self) -> None:
        """Connects the EVPService dispatch with the GoGatewayClient."""
        def dispatch_to_hardware(intersection_id: str, target_stage: int, action: str):
            try:
                from src.drivers.go_gateway_client import GoGatewayClient
                client = GoGatewayClient.get_instance()
                if client and client.is_running():
                    cmd_payload = {
                        "action_type": "activate_preempt" if action == "ACTIVATE_PREEMPT" else "release_preempt",
                        "target_stage": target_stage,
                    }
                    client.send_command("evp_preempt", intersection_id=intersection_id, action_data=cmd_payload)
            except Exception as e:
                logger.debug(f"[EVPBridge] Despacho direto de hardware (Go Gateway offline ou simulado): {e}")

        self.evp_service.on_action_dispatch = dispatch_to_hardware

    def intercept_safety_audit(
        self,
        tl_id: str,
        current_stage: int,
        stage_duration: float,
        suggested_action: int,
    ) -> Tuple[Optional[int], bool, str]:
        """
        Intercepts decision in SafetyAuditor:
        If the intersection is under active EVP preemption:
        - Returns (evp_action, was_intercepted=True, reason)
        - If not under preemption, returns (None, False, "") for normal flow.
        """
        if not self.evp_service.is_preemption_active(tl_id):
            return None, False, ""

        action, reason = self.evp_service.get_preemption_action(
            intersection_id=tl_id,
            current_stage=current_stage,
            stage_duration_seconds=stage_duration,
        )

        logger.info(f"[EVPBridge] 🛡️ Intervenção EVP no semáforo {tl_id}: Ação={action} ({reason})")
        return action, True, reason
