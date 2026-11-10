# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Agent Decision Telemetry Classifier and Reporter (SRP / Clean Architecture).
Converts approval/veto/EVP statuses into standardized codes (0 to 6) for PostgreSQL storage.
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class DecisionTelemetryReporter:
    """Classifies operational traffic light decisions and sends high-frequency metrics to the DB worker."""

    CODE_HOMOLOGATED = 0
    CODE_MIN_GREEN = 1
    CODE_YELLOW_CLEARANCE = 2
    CODE_ALL_RED = 3
    CODE_MIN_RED = 4
    CODE_SPILLBACK = 5
    CODE_EVP_PREEMPTION = 6

    @classmethod
    def classify_decision_code(
        cls, evp_override: Optional[str], guardian_vetoed: bool, reason: Optional[str]
    ) -> int:
        """Maps decision reasons and overrides to telemetry codes 0 through 6."""
        if evp_override:
            return cls.CODE_EVP_PREEMPTION
        if not guardian_vetoed:
            return cls.CODE_HOMOLOGATED

        r_upper = str(reason or "").upper()
        if "AMARELO" in r_upper or "YELLOW" in r_upper:
            return cls.CODE_YELLOW_CLEARANCE
        if "ALL_RED" in r_upper or "VERMELHO_INTEGRAL" in r_upper:
            return cls.CODE_ALL_RED
        if "MIN_RED" in r_upper or "VERMELHO" in r_upper:
            return cls.CODE_MIN_RED
        if "SPILLBACK" in r_upper or "D3QN" in r_upper or "SATURACAO" in r_upper:
            return cls.CODE_SPILLBACK
        return cls.CODE_MIN_GREEN

    @classmethod
    def push_telemetry(
        cls,
        db_manager: Any,
        tl_id: str,
        evp_override: Optional[str],
        guardian_vetoed: bool,
        reason: Optional[str],
    ) -> None:
        """Dispatches decision counts in a non-blocking manner to StepDecisionWorker."""
        if db_manager and hasattr(db_manager, "step_decision_worker"):
            try:
                code = cls.classify_decision_code(evp_override, guardian_vetoed, reason)
                db_manager.step_decision_worker.push_decision_code(agent_id=tl_id, decision_code=code, count=1)
            except Exception as ex:
                logger.debug(f"[DecisionTelemetryReporter] Falha ao enviar telemetria de decisão para {tl_id}: {ex}")
