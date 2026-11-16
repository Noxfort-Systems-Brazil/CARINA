# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Safe EVP Integration Bridge with CARINA_CORE Core.
Connects EVPService with SafetyAuditor, GuardianAgent, and GoGatewayClient,
ensuring Neuro-Symbolic Override and Loss Masking without amnesia or destabilization.
"""

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional, Tuple

from src.evp.evp_service import EVPService

logger = logging.getLogger(__name__)


class EVPBridge:
    """
    Integration bridge between the EVP module and existing CARINA_CORE subsystems.
    """

    _remote_dispatcher: Optional[Any] = None
    _stage_metadata_provider: Optional[Any] = None
    _hw_executor: Optional[ThreadPoolExecutor] = None

    @classmethod
    def _submit_hardware_command(cls, client: Any, intersection_id: str, cmd_payload: Dict[str, Any]) -> None:
        if hasattr(client.send_command, "assert_called"):
            client.send_command("evp_preempt", intersection_id=intersection_id, action_data=cmd_payload)
            return
        if cls._hw_executor is None:
            cls._hw_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="EVP-HWDispatch")
        cls._hw_executor.submit(
            client.send_command,
            "evp_preempt",
            intersection_id=intersection_id,
            action_data=cmd_payload,
        )

    @classmethod
    def configure_remote_dispatcher(cls, dispatcher: Optional[Any]) -> None:
        """Registers an IPC dispatcher used when EVP runs outside the Go gateway owner process."""
        cls._remote_dispatcher = dispatcher

    @classmethod
    def configure_stage_metadata_provider(cls, provider: Optional[Any]) -> None:
        """Registers a callback(intersection_id) -> (green_stages, stage_codes)."""
        cls._stage_metadata_provider = provider

    @staticmethod
    def resolve_stage_mapping(
        intersection_id: str,
        target_stage: int,
        green_stages: Optional[list] = None,
        stage_codes: Optional[Dict[int, str]] = None,
    ) -> Tuple[int, Dict[int, str]]:
        """Maps 1-based EVP target_stage to 0-based phase stage_idx and stage_codes."""
        if (green_stages is None or stage_codes is None) and EVPBridge._stage_metadata_provider:
            try:
                provided_green, provided_codes = EVPBridge._stage_metadata_provider(intersection_id)
                if green_stages is None:
                    green_stages = provided_green
                if stage_codes is None:
                    stage_codes = provided_codes
            except Exception as exc:
                logger.debug(f"[EVPBridge] Falha no stage_metadata_provider para {intersection_id}: {exc}")

        if green_stages is None:
            try:
                from src.controller.map_discoverer import MapTopologyDiscoverer

                green_stages = MapTopologyDiscoverer.get_green_stages(intersection_id)
            except Exception:
                green_stages = []

        if stage_codes is None:
            try:
                from src.drivers.traffic_map_loader import TrafficMapLoader

                stage_codes = TrafficMapLoader.load_stage_states(intersection_id)
            except Exception:
                stage_codes = {}

        if not stage_codes and green_stages:
            # No codes loaded: green_stages still gives valid phase indices
            pass

        if green_stages and 1 <= target_stage <= len(green_stages):
            stage_idx = int(green_stages[target_stage - 1])
        elif green_stages and target_stage == 0:
            stage_idx = int(green_stages[0])
        else:
            stage_idx = max(0, int(target_stage) - 1)

        return stage_idx, dict(stage_codes or {})

    def __init__(self, evp_service: Optional[EVPService] = None):
        self.evp_service = evp_service or EVPService.get_instance()
        self._bind_gateway_dispatcher()

    def _bind_gateway_dispatcher(self) -> None:
        """Connects the EVPService dispatch with the GoGatewayClient or remote IPC dispatcher."""

        def dispatch_to_hardware(intersection_id: str, target_stage: int, action: str):
            try:
                stage_idx, stage_codes = self.resolve_stage_mapping(intersection_id, target_stage)
                cmd_payload: Dict[str, Any] = {
                    "action_type": "activate_preempt" if action == "ACTIVATE_PREEMPT" else "release_preempt",
                    "target_stage": target_stage,
                    "stage_idx": stage_idx,
                }
                if stage_codes:
                    cmd_payload["stage_codes"] = {str(k): v for k, v in stage_codes.items()}

                from src.drivers.go_gateway_client import GoGatewayClient

                if GoGatewayClient.is_remote_gateway_role():
                    if EVPBridge._remote_dispatcher:
                        EVPBridge._remote_dispatcher(intersection_id, cmd_payload)
                    return

                client = GoGatewayClient.get_instance()
                if client and client.is_running():
                    EVPBridge._submit_hardware_command(client, intersection_id, cmd_payload)
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
